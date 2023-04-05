sudo docker compose down
sudo docker compose up -d --build
echo "Waiting for the database to be ready..."
sleep 10
pip install -r requirements.txt
python3 main.py