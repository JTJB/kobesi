# Use official nginx image
FROM nginx:alpine

# Remove the default nginx.conf and replace with ours
COPY nginx.conf /etc/nginx/nginx.conf

# Copy static files to nginx public directory
COPY index.html /usr/share/nginx/html/

# Optionally copy CSS/JS if they were separate (not needed here)
# COPY style.css /usr/share/nginx/html/
# COPY app.js /usr/share/nginx/html/

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
