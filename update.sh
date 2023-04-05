sudo pkill gunicorn
sudo docker compose down
sudo docker compose up -d --build --remove-orphans
pip install -r requirements.txt
echo "Waiting for the database to be ready..."
sleep 10
sudo docker ps
python3 main.py
# /home/ubuntu/.local/bin/gunicorn -b 0.0.0.0:5000 main:app --preload --daemon