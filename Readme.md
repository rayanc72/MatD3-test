# Installation Guide of MatD<sup>3</sup> Using Conda Environment


## Prerequisites

Before you proceed with the installation, ensure you have the following software installed on your system:

1. [Anaconda](https://www.anaconda.com/products/distribution) or [Miniconda](https://docs.conda.io/en/latest/miniconda.html)
2. Git (to clone the repository)
3. [MySQL](https://dev.mysql.com/downloads/mysql/) (If you intend to use MySQL instead of SQLite)*

[* In older macs (using intel chips), MySQL installation needs to be carried out with the legacy password option.]

## Step 1: Clone the MatD3 repository

To get started, clone the MatD3 repository from GitHub:

```bash
git clone https://github.com/HybriD3-database/MatD3.git
```


## Step 2: Create a New Conda Environment
Navigate to the MatD3 directory that was created after cloning the repository:
```bash
cd MatD3
```

create a new Conda environment for MatD3 using the following command:

```bash
conda create -n matd3_local pip
```

## Step 3: Activate the Conda Environment
Activate the newly created environment using the following command:

```bash
conda activate matd3_local
```


## Step 4: Install the Required Packages 

1. Edit the 'requirements.txt' file to remove the version requirements and mysqlclient:

```bash
Django
matplotlib
numpy
Pillow
python-dateutil
sentry-sdk
raven
python-decouple
django-nested-admin
djangorestframework
coverage
selenium
requests
Sphinx
gunicorn
sphinx_rtd_theme
django-filter>=2.4.0
```

2. to install these, use the following command:

```bash
pip install -r requirements.txt
```

3. Uncomment the following line in mainproject/settings.py:

```bash
DEFAULT_AUTO_FIELD='django.db.models.AutoField' 
```

5. Install geckodriver from conda
conda install -c conda-forge geckodriver


## Step 5: Create a .env file and Perform Additional Set-Ups, if Using MySQL

Copy the provided env.example file:

```bash
cp env.example .env
```

Additionally, if you wish to use MySQL:

1. Install MySQL client for conda
```bash
conda install -c conda-forge mysqlclient
``` 
2. in the .env file, specify that you are using MySQL:
set `USE_SQLITE=False` (the Default is `True`)

3. Create a database for using with MySQL:

```bash
mysql -u <your_mysql_username> -p 
```
This should prompt you to provide your MySQL password. After entering that, use,

```bash
create database <your_database_name>;
exit;
```

6. Update the MySQL database name, and your MySQL user info in the mainproject/settings.py file:

```bash
# Database
...
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': '<your_database_name>',
            'USER': config('DB_USER', default='<your_mysql_username>'),
            'PASSWORD': config('DB_PASSWORD', default='<your_mysql_password>'),
            'HOST': 'localhost',
            'PORT': '',
        }
    }
```


## Step 6: Initialize the Database

To Initialize static files and perform database migrations, run the following command:

```bash
./manage.py collectstatic
./manage.py migrate
```

## Step 7: Create a Superuser
Run the following command:
```bash
./manage.py createsuperuser
```

## Step 8: Start the Server
Run the following command:
```bash
./manage.py runserver
```


