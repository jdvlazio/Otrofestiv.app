#!/bin/bash
echo "=== Otrofestiv — Setup Capacitor ==="

# 1. Crear carpeta www con los archivos de la app
echo "→ Preparando carpeta www..."
mkdir -p www
cp index.html www/
cp manifest.json www/
cp sw.js www/
cp icon-192.png www/
cp icon-512.png www/
cp -r festivals www/
cp -r fonts www/
echo "  ✓ www/ lista"

# 2. Instalar dependencias
echo "→ Instalando dependencias..."
npm install --silent

# 3. Agregar plataforma Android
echo "→ Agregando Android..."
npx cap add android 2>/dev/null || true

# 4. Sincronizar
echo "→ Sincronizando..."
npx cap sync android

echo ""
echo "✓ Listo. Ahora ejecuta:"
echo "  npx cap open android"
echo ""
echo "Android Studio se abrirá con el proyecto."
echo "Presiona ▶ (Run) para instalar en tu dispositivo o emulador."
