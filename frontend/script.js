const GPTResearcher = (() => {
    const init = () => {
        document.getElementById("copyToClipboard").addEventListener("click", copyToClipboard);
        updateState("initial");
    };

    const startResearch = () => {
        console.log("Research started");
        document.getElementById("output").innerHTML = "";
        document.getElementById("reportContainer").innerHTML = "";
        updateState("in_progress");

        addAgentResponse({ output: "Подготовка отчета ..." });

        listenToSockEvents();
    };

    const listenToSockEvents = () => {
        const { protocol, host, pathname } = window.location;
        const ws_uri = `${protocol === 'https:' ? 'wss:' : 'ws:'}//${host}${pathname}ws`;
        const converter = new showdown.Converter();
        const socket = new WebSocket(ws_uri);

        socket.onopen = (event) => {
            console.log("WebSocket connection opened");
            const task = document.querySelector('input[name="task"]').value;
            const report_type = document.querySelector('select[name="report_type"]').value;
            const requestData = {
                task: task,
                report_type: report_type
            };

            socket.send(`start ${JSON.stringify(requestData)}`);
        };

        socket.onmessage = (event) => {
            console.log("Message received from WebSocket:", event.data); // Debug
            const data = JSON.parse(event.data);
            console.log("Parsed data:", data); // Debug
            if (data.type === 'logs') {
                addAgentResponse(data);
            } else if (data.type === 'report') {
                writeReport(data, converter);
            } else if (data.type === 'path') {
                updateState("finished");
                updateDownloadLink(data);
            } else if (data.type === 'progress') {
                updateProgressBar(data.output);
            }
        };

        socket.onerror = (error) => {
            console.error("WebSocket error observed:", error);
        };

        socket.onclose = (event) => {
            console.log("WebSocket connection closed:", event);
            const connectionLostMessage = "Соединение прервано...";
            alert(connectionLostMessage);

            // Refresh the page
            location.reload();
        };
    };

    const addAgentResponse = (data) => {
        const output = document.getElementById("output");
        console.log("Adding agent response:", data); // Debug
        const div = document.createElement("div");
        div.className = "agent_response";
        div.innerHTML = data.output;
        output.appendChild(div);
        output.scrollTop = output.scrollHeight;
        output.style.display = "block";
        updateScroll();
    };

    const writeReport = (data, converter) => {
        const reportContainer = document.getElementById("reportContainer");
        const markdownOutput = converter.makeHtml(data.output);
        reportContainer.innerHTML += markdownOutput;
        updateScroll();
    };

    const updateDownloadLink = (data) => {
        const path = data.output;
        const pdf_path = data.pdf_output;
        const sources_path = data.sources_output;
        document.getElementById("downloadLink").setAttribute("href", path);
        document.getElementById("downloadPdf").setAttribute("href", pdf_path);
        const sourcesButton = document.getElementById("downloadSources");
        if (sources_path) {
            sourcesButton.setAttribute("href", sources_path);
            sourcesButton.classList.remove("d-none"); 
        } else {
            sourcesButton.classList.add("d-none"); 
        }
    };
    

    const updateProgressBar = (percentage) => {
        const progressBar = document.getElementById("progressBar");
        progressBar.style.width = `${percentage}%`;
        progressBar.setAttribute("aria-valuenow", percentage);
        progressBar.textContent = `${percentage}%`;
    };

    const updateScroll = () => {
        console.log("Updating scroll"); // Debug
        const output = document.getElementById("output");
        output.scrollTop = output.scrollHeight;
    };

    const copyToClipboard = () => {
        const textarea = document.createElement('textarea');
        textarea.id = 'temp_element';
        textarea.style.height = 0;
        document.body.appendChild(textarea);
        textarea.value = document.getElementById('reportContainer').innerText;
        const selector = document.querySelector('#temp_element');
        selector.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
    };

    const updateState = (state) => {
        let status = "";
        switch (state) {
            case "in_progress":
                status = "Исследование в процессе...";
                setReportActionsStatus("disabled");
                break;
            case "finished":
                status = "Исследование завершено";
                setReportActionsStatus("enabled");
                break;
            case "error":
                status = "Ошибка сбора данных";
                setReportActionsStatus("disabled");
                break;
            case "initial":
                status = "";
                setReportActionsStatus("hidden");
                break;
            default:
                setReportActionsStatus("disabled");
        }
        document.getElementById("status").innerHTML = status;
        document.getElementById("status").style.display = status ? "block" : "none";
    };

    const setReportActionsStatus = (status) => {
        const reportActions = document.getElementById("reportActions");
        if (status === "enabled") {
            reportActions.querySelectorAll("a").forEach((link) => {
                link.classList.remove("disabled");
                link.removeAttribute('onclick');
                reportActions.style.display = "block";
            });
        } else {
            reportActions.querySelectorAll("a").forEach((link) => {
                link.classList.add("disabled");
                link.setAttribute('onclick', "return false;");
            });
            if (status === "hidden") {
                reportActions.style.display = "none";
            }
        }
    };

    document.addEventListener("DOMContentLoaded", init);
    return {
        startResearch,
        copyToClipboard,
    };
})();

// Функция для обработки авторизации
function handleLogin(event) {
    event.preventDefault(); // Предотвращаем стандартную отправку формы

    if (validateLoginForm()) {
        sendLoginData()
            .then(() => {
                const authContainer = document.querySelector('.container.my-5');
                authContainer.style.display = 'none';

                const researchForm = document.querySelector('form.mt-3');
                researchForm.classList.remove('d-none');

                const progressResearch = document.querySelector('div.margin-div');
                progressResearch.classList.remove('d-none');

                const progressReport = document.querySelector('div.margin-div.d-none');
                progressReport.classList.remove('d-none');

                const backTop = document.querySelector("#back-to-top");
                backTop.classList.remove('d-none');
                
            })
            .catch((error) => {
                alert('Ошибка авторизации: ' + error.message);
            });
    }

    return false; // Предотвращаем отправку формы
}

// Функция для отправки данных авторизации на сервер
async function sendLoginData() {
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');

    const response = await fetch('/login', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            username: usernameInput.value,
            password: passwordInput.value
        })
    });

    if (response.ok) {
        return; // Авторизация успешна
    } else {
        throw new Error('Неверное имя пользователя или пароль.');
    }
}

// Валидация полей формы авторизации
function validateLoginForm() {
    const usernameInput = document.getElementById('username');
    const passwordInput = document.getElementById('password');

    if (usernameInput.value.trim() === '') {
        alert('Пожалуйста, введите имя пользователя.');
        return false;
    }

    if (passwordInput.value.trim() === '') {
        alert('Пожалуйста, введите пароль.');
        return false;
    }

    return true;
}