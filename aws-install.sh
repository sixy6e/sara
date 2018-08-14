sudo yum-config-manager --disable pgdg95
sudo yum update
sudo rpm -Uvh http://dl.fedoraproject.org/pub/epel/6/x86_64/epel-release-6-8.noarch.rpm
sudo rpm -Uvh http://elgis.argeo.org/repos/6/elgis-release-6-6_0.noarch.rpm
sudo amazon-linux-extras install nginx1.12
sudo yum install -y git wget unzip postfix mailx php php-pgsql php-xml php-fpm python-pip python3
sudo pip3 install requests

sudo yum install -y gcc-c++ make
curl -sL https://rpm.nodesource.com/setup_6.x | sudo -E bash -
sudo yum install -y nodejs

sudo npm install -g grunt-cli
sudo npm install -g json


echo " >>> Create configuration file /etc/nginx/default.d/sara.conf"
cat <<EOF > /etc/nginx/default.d/sara.conf
  endfile_max_chunk  2m;
  aio                on;

  location ~ \.php\$ {
      include /etc/nginx/fastcgi_params;
      fastcgi_param   SCRIPT_FILENAME  \$document_root\$fastcgi_script_name;
      fastcgi_split_path_info ^(.+\.php)(/.+)\$;
      fastcgi_pass  127.0.0.1:9000;
      fastcgi_index index.php;
  }
  location /sara.server/1.0/ {
    if (!-e \$request_filename) {
      rewrite ^/sara.server/1.0/(.*)\$ /sara.server/1.0/index.php?RESToURL=\$1 last; break;
    }
  }
  # path to zip files     
  location ~ \.zip {
    root /;     
  }
  # Quicklook files
  location ${SARA_DATA_URL} {
    alias ${DATA_ROOT_PATH};
  }
  location ~ /\.ht {
    deny all;
  }
  # Protect config files
  location ~* ^config.\.php\$ {
    return 404;
  }
EOF
