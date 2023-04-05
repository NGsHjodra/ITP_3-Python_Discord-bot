sudo docker compose down
sudo docker compose up -d # --build
echo "Waiting for the database to be ready..."
sleep 5
sudo service postgresql status
sleep 1
pip install -r requirements.txt
python3 main.py