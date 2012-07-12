app=scalrr
serverdir=/var/www/
appsources="scalrr.py scidb_server_interface.py mysql_server_interface.py templates static"
appenvdir=venv

echo NOTE: assuming apache2, libapache2-mod-wsgi, virtualenv and pip packages are already installed
echo NOTE: run \"sudo apt-get install apache2 libapache2-mod-wsgi virtalenv pip\" to install these packages
echo NOTE: if you have permission issues running this script, try running it with sudo:
echo \"\tsudo ./server_setup.sh\"

echo removing application directory $serverdir$app
rm -rf $serverdir$app
echo creading application directory $serverdir$app
mkdir $serverdir$app
echo copying app.wsgi file and moving it to $serverdir$app
cp $app.wsgi app.wsgi
echo from $app import app as application >> app.wsgi
mv $app.wsgi $serverdir$app
echo copying app files and folders to $serverdir$app
cp -R $appsources $serverdir$app
echo setting up virtual python environment
cd $serverdir$app
mkdir $appenvdir
virtualenv $appenvdir
echo activating virtual environment
echo NOTE: don\'t forget to deactivate virtal environment when done!
. $appenvdir/bin/activate
echo installing flask in virtual environment
pip install Flask
