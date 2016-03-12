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

@app.route("/containers")
def containers():
    
    #if request.method == 'POST':
    #    Image=request.form['image']
    #    print "image = " + Image

    #else:
    return render_template('containers.html')

@app.route("/images")
def images():
    return render_template('images.html')

@app.route("/new_container")
def new_container():
    return render_template('new_container.html')

@app.route('/hello', methods=['POST'])
def hello():
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
    print Image, type(Command), HostName, User, Ports, Volumes, Name, Cpu_Shares, Working_Directory, Detach, Network_Disabled, type(Tty), Std_Open
    container = cli.create_container(image=str(Image), command=None, tty=True)
    #command=Command, hostname=HostName, user=User, ports=Ports, volumes=Volumes, 
    #name=Name, cpu_shares=Cpu_Shares, working_dir=Working_Directory, detach=Detach, network_disabled=Network_Disabled, tty=Tty,
    #stdin_open=Std_Open)
    cli.start(container)
    
    print "image = " + Image
    return redirect('/containers')

@socketio.on('req_api_containers')
def req_api_containers():
    resp = cli.containers()
    emit('resp_api_containers', resp)

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

@socketio.on('req_api_images')
def req_api_images():
    resp = cli.images()
    emit('resp_api_images', resp)




if __name__ == "__main__":
	cli = Client(base_url="unix://var/run/docker.sock")
	socketio.run(app, host='0.0.0.0')
