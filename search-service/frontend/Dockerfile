FROM nginx:alpine

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Add our config as a template — nginx will run envsubst on it at startup
COPY nginx.conf /etc/nginx/templates/default.conf.template

# Copy all frontend static files (index.html, css/, js/)
COPY static/ /usr/share/nginx/html/
