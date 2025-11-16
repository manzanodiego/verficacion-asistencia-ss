
import {Html5Qrcode} from "html5-qrcode";

//Validar espacios


function escanear_qr(text_decodificado){
    document.getElementById('result').innerHTML = "Codigo escaneado" + text_decodificado;

    fetch('/leer_qr',{
        method: 'POST',
        headers:{
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({qr_data:text_decodificado})
    })
    .then(response => response.json())
    .then(data => console.log(data))
    .then((error) => console.error('error: ', error));

    const html5Qrcode = new Html5Qrcode("reader");
    Html5Qrcode.start({facingMode: "enviroment"}, {fps:10, qrbox:250}).render(escanear_qr);
}