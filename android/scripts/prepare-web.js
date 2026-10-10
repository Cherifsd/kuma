// Copie l'interface Kuma (../static/index.html) dans www/ pour l'application.
const fs = require("fs"), path = require("path");
const src = path.join(__dirname, "..", "..", "static", "index.html");
const www = path.join(__dirname, "..", "www");
fs.mkdirSync(www, { recursive: true });
let html = fs.readFileSync(src, "utf8");
// Le script Capacitor est injecté automatiquement par l'application native.
fs.writeFileSync(path.join(www, "index.html"), html);
console.log("Interface copiée dans www/");
