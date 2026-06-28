const GPTResearcher = (() => {
    let pollIntervalId = null;
    let lastLogCount = 0;
    let lastReportChunkCount = 0;

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

        startTask();
    };

    const startTask = async () => {
        const converter = new showdown.Converter();
        const task = document.querySelector('input[name="task"]').value;
        const report_type = document.querySelector('select[name="report_type"]').value;

        lastLogCount = 0;
        lastReportChunkCount = 0;
        clearPolling();

        try {
            const response = await fetch('/api/tasks', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ task, report_type })
            });

            if (!response.ok) {
                throw new Error('Не удалось запустить задачу');
            }

            const data = await response.json();
            await pollTask(data.task_id, converter);
            pollIntervalId = setInterval(() => pollTask(data.task_id, converter), 1500);
        } catch (error) {
            console.error("Task start error:", error);
            updateState("error");
            alert("Ошибка запуска задачи. Попробуйте снова или обратитесь к администратору.");
        }
    };

    const pollTask = async (taskId, converter) => {
        try {
            const response = await fetch(`/api/tasks/${taskId}`);
            if (!response.ok) {
                throw new Error('Не удалось получить статус задачи');
            }

            const data = await response.json();
            syncLogs(data.logs || []);
            syncReport(data.report_chunks || [], converter);
            updateProgressBar(data.progress || 0);

            if (data.result && data.result.output) {
                updateDownloadLink(data.result);
            }

            if (data.status === 'finished') {
                updateState("finished");
                clearPolling();
            } else if (data.status === 'failed') {
                updateState("error");
                clearPolling();
                const errorMessage = data.error || "Ошибка выполнения задачи.";
                addAgentResponse({ output: errorMessage });
                alert(errorMessage);
            }
        } catch (error) {
            console.error("Polling error:", error);
            updateState("error");
            clearPolling();
            alert("Ошибка получения статуса задачи. Попробуйте снова.");
        }
    };

    const clearPolling = () => {
        if (pollIntervalId) {
            clearInterval(pollIntervalId);
            pollIntervalId = null;
        }
    };

    const syncLogs = (logs) => {
        for (let i = lastLogCount; i < logs.length; i += 1) {
            addAgentResponse({ output: logs[i] });
        }
        lastLogCount = logs.length;
    };

    const syncReport = (reportChunks, converter) => {
        for (let i = lastReportChunkCount; i < reportChunks.length; i += 1) {
            writeReport({ output: reportChunks[i] }, converter);
        }
        lastReportChunkCount = reportChunks.length;
    };

    const addAgentResponse = (data) => {
        const output = document.getElementById("output");
        console.log("Adding agent response:", data);
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
        console.log("Updating scroll");
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
    }
    throw new Error('Неверное имя пользователя или пароль.');
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
