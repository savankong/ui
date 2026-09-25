#!/usr/bin/env bash
# Creates (or reuses) a DigitalOcean droplet and serves this project with nginx.
# Auth: the environment's API credential for api.digitalocean.com is injected by the
# session proxy; locally, export DIGITALOCEAN_ACCESS_TOKEN instead.
#   scripts/deploy_do.sh            create/reuse droplet "one-shape" and upload
# Env: DO_REGION (default nyc3), DO_SIZE (default s-1vcpu-1gb), DO_NAME (default one-shape)
set -euo pipefail
cd "$(dirname "$0")/.."
NAME=${DO_NAME:-one-shape}; REGION=${DO_REGION:-nyc3}; SIZE=${DO_SIZE:-s-1vcpu-1gb}
KEY=${DO_SSH_KEY:-$HOME/.ssh/one_shape_ed25519}
API=https://api.digitalocean.com/v2
auth=(); [ -n "${DIGITALOCEAN_ACCESS_TOKEN:-}" ] && auth=(-H "Authorization: Bearer $DIGITALOCEAN_ACCESS_TOKEN")
do_api() { curl -sSf "${auth[@]}" -H "Content-Type: application/json" "$@"; }

[ -f "$KEY" ] || ssh-keygen -q -t ed25519 -N "" -C one-shape-deploy -f "$KEY"
FP=$(ssh-keygen -E md5 -lf "$KEY.pub" | awk '{print $2}' | sed 's/^MD5://')
do_api "$API/account/keys/$FP" >/dev/null 2>&1 || \
  do_api -X POST "$API/account/keys" -d "{\"name\":\"one-shape-deploy\",\"public_key\":\"$(cat "$KEY.pub")\"}" >/dev/null

ID=$(do_api "$API/droplets?tag_name=one-shape" | python3 -c "import json,sys;d=[x for x in json.load(sys.stdin)['droplets'] if x['name']=='$NAME'];print(d[0]['id'] if d else '')")
if [ -z "$ID" ]; then
  USERDATA=$'#cloud-config\npackages: [nginx]\nruncmd:\n  - mkdir -p /var/www/one-shape\n  - sed -i "s#root /var/www/html;#root /var/www/one-shape;#" /etc/nginx/sites-available/default\n  - systemctl restart nginx\n'
  BODY=$(python3 -c "import json,sys;print(json.dumps({'name':'$NAME','region':'$REGION','size':'$SIZE','image':'ubuntu-24-04-x64','ssh_keys':['$FP'],'tags':['one-shape'],'user_data':sys.argv[1]}))" "$USERDATA")
  ID=$(do_api -X POST "$API/droplets" -d "$BODY" | python3 -c "import json,sys;print(json.load(sys.stdin)['droplet']['id'])")
  echo "created droplet $ID"
fi
for _ in $(seq 60); do
  IP=$(do_api "$API/droplets/$ID" | python3 -c "import json,sys;d=json.load(sys.stdin)['droplet'];n=[x['ip_address'] for x in d['networks']['v4'] if x['type']=='public'];print(n[0] if d['status']=='active' and n else '')")
  [ -n "$IP" ] && break; sleep 5
done
[ -n "$IP" ] || { echo "droplet $ID not active yet" >&2; exit 1; }
SSH=(ssh -i "$KEY" -o StrictHostKeyChecking=accept-new -o ConnectTimeout=10 root@"$IP")
for _ in $(seq 60); do "${SSH[@]}" 'test -d /var/www/one-shape && systemctl is-active --quiet nginx' 2>/dev/null && break; sleep 5; done
tar czf - index.html assets/fonts out/one-shape.mp4 out/loop.m4a | "${SSH[@]}" 'tar xzf - -C /var/www/one-shape'
echo "live: http://$IP/   video: http://$IP/out/one-shape.mp4"
