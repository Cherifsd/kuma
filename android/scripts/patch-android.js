// Ajoute au projet Android : autorisation du micro et connexion http vers l'ordinateur (Wi-Fi local).
const fs = require("fs"), path = require("path");
const manifest = path.join(__dirname, "..", "android", "app", "src", "main", "AndroidManifest.xml");
let xml = fs.readFileSync(manifest, "utf8");
const perms = [
  "android.permission.RECORD_AUDIO",
  "android.permission.MODIFY_AUDIO_SETTINGS",
  "android.permission.INTERNET",
];
for (const p of perms) {
  if (!xml.includes(`"${p}"`)) {
    xml = xml.replace("</manifest>", `    <uses-permission android:name="${p}" />\n</manifest>`);
  }
}
if (!xml.includes("usesCleartextTraffic")) {
  xml = xml.replace("<application", '<application\n        android:usesCleartextTraffic="true"');
}
fs.writeFileSync(manifest, xml);
console.log("AndroidManifest.xml : micro + http local activés");
