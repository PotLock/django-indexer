#!/bin/bash
echo 'run after_install.sh' >> /home/ec2-user/myrepo/deploy.log

cd /home/ec2-user/django-indexer

echo 'poetry install' >> /home/ec2-user/myrepo/deploy.log 

poetry shell

poetry install >> /home/ec2-user/myrepo/deploy.log