#!/usr/bin/env bash
set -e

echo -e "\033[42mGet environments\033[0m"
set -a &&  . ../opt/starburger/.env && set +a

echo -e "\033[42mStart git pull\033[0m"
cd ../opt/starburger && git pull

echo  -e "\033[42mStart install Python libraries\033[0m"
source venv/bin/activate && pip install -r requirements.txt

echo -e "\033[42mStart install Node.js libraries\033[0m"
npm ci --dev
echo -e "\033[42mRebuild frontend\033[0m"
./node_modules/.bin/parcel build bundles-src/index.js --dist-dir bundles --public-url="./"

echo -e "\033[42mCollect static\033[0m"
python manage.py collectstatic --no-input
echo -e "\033[42mMigrate database\033[0m"
python manage.py migrate --no-input

echo -e "\033[42mRestart starburger service\033[0m"
systemctl restart starburger.service
echo -e "\033[42mReload nginx service\033[0m"
systemctl reload nginx.service

echo -e "\033[42mNotify Rollbar about deployment\033[0m"
curl -H "X-Rollbar-Access-Token: $ROLLBAR_POST_SERVER_ITEM_ACCESS_TOKEN" -H "Content-Type: application/json" -X POST 'https://api.rollbar.com/api/1/deploy' -d '{"environment": "production", "revision": "'$(git rev-parse HEAD)'", "rollbar_name": "riminprog", "local_username": "riminprog"}'

echo -e "\033[42mDeploy process finish successefully!\033[0m"
