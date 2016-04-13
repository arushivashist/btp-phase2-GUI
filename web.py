import datetime
import threading
import time
from docker import Client
from flask import (
	Flask,
	render_template,
    url_for,
    request,
    redirect
)
from flask.ext.socketio import SocketIO, emit

app = Flask(__name__)
socketio = SocketIO(app)
cli = None
container_threads = {}
cpu_old = {}

class ContainerThreadClass(threading.Thread):
    def __init__(self, cont_id):
        super(ContainerThreadClass, self).__init__()
        self._stopper = threading.Event()
        self._cont_id = cont_id
        self._stats_stream = cli.stats(cont_id, decode=True)
        self._stats = {}
    def run(self):
        for i in self._stats_stream:
            self._stats = i
            time.sleep(0.1)
            if self._stopper.isSet():
                break
    def stop(self):
        self._stopper.set()


@app.route("/containers")
def containers():
    return render_template('containers.html')

@app.route("/images")
def images():
    return render_template('images.html')

@app.route("/new_container")
def new_container():
    return render_template('new_container.html')

@app.route("/container_info")
def container_info():
    cont_id = request.args.get('cont_id')
    conts = cli.containers()
    cont = None
    for x in conts:
        if cont_id == x['Id']:
            cont = x
            break
    if cont:
        cont['Created'] = datetime.datetime.fromtimestamp(cont['Created']).strftime('%Y-%m-%d %H:%M:%S')
        return render_template('container_info.html', cont=cont)
    else:
        return render_template('containers.html')

@app.route("/container_pty")
def container_pty():
    cont_id = request.args.get('cont_id')
    cont = cli.inspect_container(cont_id)
    return render_template('container_pty.html', cont=cont)

@app.route('/api_new_container', methods=['POST'])
def api_new_container():
    Image = request.form['image']
    if request.form['command'].encode("utf-8") == None:
        print "yes"
    Command = request.form['command']
    HostName = request.form['hostname']
    User = request.form['user']
    Ports = request.form['ports']
    Volumes = request.form['volumes']
    Name = request.form['name']
    Cpu_Shares = request.form['cpu_shares']
    Working_Directory = request.form['working_dir']
    Detach = request.form['detach']
    Network_Disabled = request.form['network_disabled']
    Tty = request.form['tty']
    Std_Open = request.form['stdin_open']
#    print Image, Command, HostName, User, Ports, Volumes, Name, Cpu_Shares, Working_Directory, Detach, Network_Disabled, type(Tty), Std_Open
    print str(Volumes)
#    container = cli.create_container(image=str(Image), command=None, tty=True, hostname=str(HostName), host_config=cli.create_host_config(binds=[str(Volumes)]))
    if str(Volumes) == "None":
        container = cli.create_container(image=str(Image), command=None, tty=True, hostname=str(HostName))
    else:
        container = cli.create_container(image=str(Image), command=None, tty=True, hostname=str(HostName), host_config=cli.create_host_config(binds=[str(Volumes)]))
    #command=Command, hostname=HostName, user=User, ports=Ports, volumes=Volumes, 
    #name=Name, cpu_shares=Cpu_Shares, working_dir=Working_Directory, detach=Detach, network_disabled=Network_Disabled, tty=Tty,
    #stdin_open=Std_Open)
    cli.start(container)
    
    print "image = " + Image
    return redirect('/containers')

@socketio.on('req_api_containers')
def req_api_containers():
    resp = cli.containers()
    print container_threads
    for cont in resp:
        if cont[u'Id'] not in container_threads:
            t = ContainerThreadClass(cont[u'Id'])
            container_threads[cont[u'Id']] = t
            t.start()
    emit('resp_api_containers', resp)

@socketio.on('req_api_container_info')
def req_api_container_info(json):
    print json
    print container_threads
    if json['cont_id'] in container_threads:
        cpu_new = container_threads[json['cont_id']]._stats['cpu_stats']
        if json['cont_id'] in cpu_old:
            resp = {'cpu_old': cpu_old[json['cont_id']], 'cpu_new': cpu_new}
            emit('resp_api_container_info', resp)
        cpu_old[json['cont_id']] = cpu_new

@socketio.on('req_api_start_container')
def req_api_start_container(json):
    container = cli.create_container(image=json["contName"], command='', tty=True)
    cli.start(container)

@socketio.on('req_api_stop_container')
def req_api_stop_container(json):
    resp = cli.containers()
    for cont in resp:
        if cont["Id"] == json["contId"]:
            try:
                cli.kill(cont)
            except APIError:
                cli.wait(cont)
            try:
                cli.stop(cont)
            except APIError:
                pass
            break

@socketio.on('req_api_container_pty')
def req_api_container_pty(json):
    exec_id = cli.exec_create(json['cont_id'], json['cmd'])
    cmd_out = cli.exec_start(exec_id)
    emit('resp_api_container_pty', cmd_out)

@socketio.on('req_api_images')
def req_api_images():
    resp = cli.images()
    emit('resp_api_images', resp)




if __name__ == "__main__":
	cli = Client(base_url="unix://var/run/docker.sock")
	socketio.run(app, host='0.0.0.0')
