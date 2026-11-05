root /usr/share/nginx/html;
access_log /var/log/nginx/access.log orders;
client_max_body_size 16k;
add_header X-Content-Type-Options nosniff always;
add_header Referrer-Policy no-referrer always;
add_header Content-Security-Policy "default-src 'self'; frame-ancestors 'none'; base-uri 'none'; object-src 'none'" always;
location /api/ops/ {
    resolver 127.0.0.11 valid=5s ipv6=off;
    set $observer http://monitor:8000;
    proxy_pass $observer;
    proxy_connect_timeout 1s;
    proxy_read_timeout 6s;
}
location /api/ {
    proxy_pass http://order_api;
    proxy_http_version 1.1;
    proxy_connect_timeout 1s;
    proxy_read_timeout 8s;
    proxy_next_upstream error timeout http_502 http_503 http_504 non_idempotent;
    proxy_next_upstream_tries 2;
}
location = /operaciones {
    try_files /index.html =404;
}
location / {
    try_files $uri $uri/ =404;
}
