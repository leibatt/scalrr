app=scalrr
serverdir=/var/www/
appsources="scalrr.py scidb_server_interface.py mysql_server_interface.py templates static"
appenvdir=venv
confdir=/etc/apache2/sites-available/
confname=example.com

echo NOTE: assuming apache2, libapache2-mod-wsgi, virtualenv and pip packages are already installed
echo NOTE: run \"sudo apt-get install apache2 libapache2-mod-wsgi virtalenv pip\" on the command line to install these packages
echo NOTE: if you have permission issues running this script, try running it on the command line with sudo:
echo \t\"sudo ./server_setup.sh\"

echo removing application directory $serverdir$app
rm -rf $serverdir$app
echo creading application directory $serverdir$app
mkdir $serverdir$app
echo copying app.wsgi file to $serverdir$app
cp $app.wsgi $serverdir$app
#echo copying app files and folders to $serverdir$app
#cp -R $appsources $serverdir$app
echo moving $confname file to $confdir
cp $confname $confdir
echo setting up virtual python environment
mkdir $appenvdir
virtualenv $appenvdir
echo activating virtual environment
echo NOTE: don\'t forget to deactivate virtual environment when done!
echo NOTE: just type \"deactivate\" on the command line to deactivate virtual environment
. $appenvdir/bin/activate
echo installing flask and simplejson python libraries in virtual environment
pip install Flask
pip install simplejson
echo installing MySQLdb python library in virtual environment
echo NOTE: to skip the mysql stuff comment this out in the script
echo \tand comment out the accompanying mysql-related code in $app.py
pip install MySQL-python

