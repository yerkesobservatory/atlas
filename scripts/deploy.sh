if [[ !( -a /live/seo/) && ($HOST != 'sirius') ]]
then
    echo "Copying deploy script to sirius..."
    # copy deploy to /tmp on server
    scp deploy.sh rprechelt@sirius.stoneedgeobservatory.com:/tmp/

    # ssh to live server
    ssh -t rprechelt@sirius.stoneedgeobservatory.com "sudo sh /tmp/deploy.sh"
else
    echo "Starting deployment..."
    # copy live version to backup
    echo "About to make a backup of the seo-repo..."
    read -n 1
    cd /live/seo
    COMMIT=`git rev-parse HEAD`
    COMMIT_SHORT="${COMMIT: -8}"
    cp -rf seo /live/backups/seo-${COMMIT_SHORT}

    # get the latest version of the code
    echo "About to update seo/ to the latest code version..."
    read -n 1
    cd /live/seo
    git fetch --all
    git reset --hard origin/master

    # update python packages
    echo "About to update python packages..."
    read -n 1
    source .env/bin/activate
    pip install -r requirements/server.txt
    pip install -r requirements/web.txt
    deactivate

    # change permissions for web directory
    echo "About to change permissions on /live/seo/web..."
    read -n 1
    chown -R rprechelt:nginx /live/seo
    chmod -R 710 /live/seo/web
    chmod 710 /live/seo

    # copy image files into place (until git-lfs bug is fixed)
    echo "About to copy image files into place..."
    read -n 1
    cp /live/images/*.png /live/seo/web/app/static/images/

    # updating symlink
    echo "About to update systemd symlinks..."
    read -n 1
    cd /etc/systemd/system
    for service in `ls /live/seo/services/*.service`; do
	ln -sf $service
    done
    ln -sf /live/seo/services/seo.target

    # reload systemd services
    systemctl daemon-reload

    # restart seo services
    echo "About to restart seo.services..."
    read -n 1
    systemctl restart seo-broker
    systemctl restart seo-queue
    systemctl restart seo-web

    # restart nginx
    echo "About to restart nginx..."
    read -n 1
    systemctl restart nginx

    # ALL DONE
    echo "Code has been successfully deployed; go to stoneedgeobservatory.com to verify operation"
fi
