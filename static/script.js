async function uploadPDF(){

    let pdfInput=document.getElementById("pdf");

    let file=pdfInput.files[0];

    if(!file){
        alert("Please select a PDF file first");
        return;
    }

    let formData=new FormData();
    formData.append("pdf",file);

    const res=await fetch("/upload",{

        method:"POST",

        body:formData

    });

    const data=await res.json();

    if(data.status==="success"){
        alert("PDF uploaded successfully!");
        document.getElementById("pdf").value="";
    } else {
        alert("Error uploading PDF: "+data.message);
    }

}

async function askQuestion(){

    let q=document.getElementById("question").value;

    let chat=document.getElementById("chat");

    chat.innerHTML+=`
    <div class="user">
    <p>${q}</p>
    </div>
    `;

    const res=await fetch("/ask",{

        method:"POST",

        headers:{
            "Content-Type":"application/json"
        },

        body:JSON.stringify({

            question:q

        })

    });

    const data=await res.json();

    chat.innerHTML+=`
    <div class="bot">
    <p>${data.answer}</p>
    </div>
    `;

}