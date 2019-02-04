
//Freeze requirements
pip freeze > requirements.txt

//Installing Redis
sudo apt install redis-server
//Change the init system directive supervised to use systemd
sudo nano /etc/redis/redis.conf

Change 
supervised no 
to 
supervisedsystemd

sudo systemctl restart redis.service



//Install Postgres, create db and user
apt-get install postgresql postgresql-contrib
sudo -u postgres psql
CREATE DATABASE searchtooldb;
CREATE USER searchtooladmin WITH ENCRYPTED PASSWORD '%YOUR_PASSWORD_HERE%';
GRANT ALL PRIVILEGES ON DATABASE searchtooldb TO searchtooladmin;

//Edit the pg_hba.conf,
/etc/postgresql/10/main/pg_hba.conf
//To allow password verfication of user searchtooladmin for all databases.

//To run the server, run gunicorn
gunicorn --bind 0.0.0.0:8000 wsgi

45.55.46.98:8000



//Start redis processes with
python redis_worker.py 1


