#!/usr/bin/env bash

cd /app
sudo apt-get update -u 

update_python(){
    sudo add-apt-repository -y ppa:deadsnakes/ppa
    sudo apt-get update
    sudo apt-get install -y python3.6 python3-pip python3.6-dev python3-gdbm
    sudo cp /usr/lib/python3/dist-packages/apt_pkg.cpython-35m-x86_64-linux-gnu.so /usr/lib/python3/dist-packages/apt_pkg.so
}

install_project_dependencies(){
    sudo apt-get install -y supervisor netcat
    sudo apt-get install -y build-essential autoconf libtool pkg-config python-opengl python-imaging python-pyrex python-pyside.qtopengl idle-python2.7 qt4-dev-tools qt4-designer libqtgui4 libqtcore4 libqt4-xml libqt4-test libqt4-script libqt4-network libqt4-dbus python-qt4 python-qt4-gl libgle3 python-dev libssl-dev
}

set_default_python(){
    sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.5 1
    sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.6 10
    sudo update-alternatives --config -y python3
}

configure_supervisor(){
    cp /app/vagrant/mrm_api.conf /etc/supervisor/conf.d/mrm_api.conf
}
create_virtual_environment(){
    pip3 install virtualenv 
    virtualenv -p python3 venv
    source venv/bin/activate 
}

app_setup(){
    pip install -r requirements.txt && 
    pip install gunicorn && \
    pip install gevent 
}

run_app(){
    sudo systemctl enable supervisor
    sudo systemctl start supervisor
    sudo supervisorctl reread
    sudo supervisorctl update
    sudo supervisorctl start mrm_api
}

update_python
install_project_dependencies
set_default_python
configure_supervisor
create_virtual_environment
app_setup
run_app
