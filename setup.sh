if [ "$EUID" -ne 0 ]
    then echo "This script requires sudo to run."
    exit
fi
apt install -y python3
pip install -r requirements.txt
flask --app "medusa" run
