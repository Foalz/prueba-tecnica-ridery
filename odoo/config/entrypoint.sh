#!/bin/bash
# entrypoint.sh: Genera odoo.conf dinámicamente a partir de variables de entorno

cat <<EOF > /tmp/odoo.conf
[options]
admin_passwd = ${ODOO_ADMIN_PASSWORD:-$PASSWORD}
addons_path = /mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons
db_host = db
db_port = 5432
db_user = ${USER}
db_password = ${PASSWORD}
workers = 0
limit_time_cpu = 600
limit_time_real = 1200
limit_memory_hard = 2684354560
limit_memory_soft = 2147483648
log_level = info
EOF

# Ejecutar el entrypoint oficial de Odoo inyectando el archivo generado
exec /entrypoint.sh odoo -c /tmp/odoo.conf "$@"
