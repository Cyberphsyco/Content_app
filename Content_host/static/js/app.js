async function generateScript() {

    const topic =
        document.getElementById("scriptTopic").value.trim();

    const niche =
        document.getElementById("scriptNiche").value.trim();

    const audience =
        document.getElementById("scriptAudience").value.trim();

    const platform =
        document.getElementById("scriptPlatform").value.trim();

    const goal =
        document.getElementById("scriptGoal").value.trim();

    const button =
        document.getElementById("generateScriptButton");

    const result =
        document.getElementById("scriptResult");


    if (!topic) {

        alert("Please enter a topic.");

        return;
    }


    button.disabled = true;

    button.innerText = "Writing...";


    result.innerHTML = `

        <div class="loading-result">

            <div class="loader"></div>

            <h2>Writing your script...</h2>

            <p>
                ContentAI is creating your Hook, Body and CTA.
            </p>

        </div>

    `;


    try {

        const response = await fetch(
            "/generate-script",
            {

                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({

                    topic,
                    niche,
                    audience,
                    platform,
                    goal

                })

            }
        );


        const data = await response.json();


        if (!data.success) {

            throw new Error(
                data.error || "Something went wrong."
            );

        }


        const script = data.script;


        result.innerHTML = `

            <div class="generated-script">

                <div class="result-header">

                    <div>

                        <span class="result-label">
                            GENERATED SCRIPT
                        </span>

                        <h2>
                            ${escapeHTML(script.title)}
                        </h2>

                    </div>

                    <button
                        onclick="copyScript()"
                        class="copy-button"
                    >
                        Copy
                    </button>

                </div>


                <div id="copyContent">

                    <div class="script-section">

                        <div class="section-label hook-label">
                            HOOK
                        </div>

                        <p>
                            ${escapeHTML(script.hook)}
                        </p>

                    </div>


                    <div class="script-section">

                        <div class="section-label body-label">
                            BODY
                        </div>

                        <p>
                            ${escapeHTML(script.body)}
                        </p>

                    </div>


                    <div class="script-section">

                        <div class="section-label cta-label">
                            CTA
                        </div>

                        <p>
                            ${escapeHTML(script.cta)}
                        </p>

                    </div>

                </div>

            </div>

        `;


    } catch (error) {

        result.innerHTML = `

            <div class="error-result">

                <h2>
                    Couldn't generate the script
                </h2>

                <p>
                    ${escapeHTML(error.message)}
                </p>

            </div>

        `;

    }


    button.disabled = false;

    button.innerText = "Generate Script";

}


async function generateIdeas() {

    const niche =
        document.getElementById("ideaNiche").value.trim();

    const audience =
        document.getElementById("ideaAudience").value.trim();

    const platform =
        document.getElementById("ideaPlatform").value.trim();

    const goal =
        document.getElementById("ideaGoal").value.trim();

    const button =
        document.getElementById("generateIdeasButton");

    const grid =
        document.getElementById("ideasGrid");


    if (!niche) {

        alert("Please enter your niche.");

        return;
    }


    button.disabled = true;

    button.innerText = "Generating...";


    try {

        const response = await fetch(
            "/generate-ideas",
            {

                method: "POST",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({

                    niche,
                    audience,
                    platform,
                    goal

                })

            }
        );


        const data =
            await response.json();


        if (!data.success) {

            throw new Error(
                data.error
            );

        }


        grid.innerHTML = "";


        data.ideas.forEach(
            (idea, index) => {

                const card =
                    document.createElement("div");

                card.className =
                    "idea-card";


                card.innerHTML = `

                    <div class="idea-number">
                        ${index + 1}
                    </div>

                    <div>

                        <h3>
                            ${escapeHTML(idea.title)}
                        </h3>

                        <p>
                            ${escapeHTML(idea.description)}
                        </p>

                    </div>

                `;


                grid.appendChild(card);

            }
        );


    } catch (error) {

        alert(
            error.message ||
            "Could not generate ideas."
        );

    }


    button.disabled = false;

    button.innerText =
        "Generate 10 Ideas";

}


function toggleScript(id) {

    const item =
        document.getElementById(
            `script-${id}`
        );


    if (!item) {
        return;
    }


    item.classList.toggle(
        "expanded"
    );

}


function searchScripts() {

    const search =
        document
            .getElementById("scriptSearch")
            .value
            .toLowerCase()
            .trim();


    const scripts =
        document.querySelectorAll(
            ".script-item"
        );


    scripts.forEach(
        script => {

            const title =
                script.dataset.title || "";

            const platform =
                script.dataset.platform || "";


            const matches =
                title.includes(search) ||
                platform.includes(search);


            script.style.display =
                matches ? "flex" : "none";


            const id =
                script.getAttribute(
                    "onclick"
                );


        }
    );

}


async function deleteScript(id) {

    const confirmed =
        confirm(
            "Delete this script?"
        );


    if (!confirmed) {
        return;
    }


    try {

        const response =
            await fetch(
                `/content/${id}/delete`,
                {
                    method: "POST"
                }
            );


        const data =
            await response.json();


        if (data.success) {

            location.reload();

        } else {

            alert(
                data.error ||
                "Could not delete script."
            );

        }

    } catch (error) {

        alert(
            "Something went wrong."
        );

    }

}


async function deleteIdea(id) {

    const confirmed =
        confirm(
            "Delete this idea?"
        );


    if (!confirmed) {
        return;
    }


    try {

        const response =
            await fetch(
                `/idea/${id}/delete`,
                {
                    method: "POST"
                }
            );


        const data =
            await response.json();


        if (data.success) {

            location.reload();

        } else {

            alert(
                data.error ||
                "Could not delete idea."
            );

        }

    } catch (error) {

        alert(
            "Something went wrong."
        );

    }

}


async function copyScript() {

    const content =
        document.getElementById(
            "copyContent"
        );


    if (!content) {
        return;
    }


    const text =
        content.innerText;


    try {

        await navigator.clipboard.writeText(
            text
        );


        alert(
            "Script copied!"
        );

    } catch (error) {

        alert(
            "Could not copy script."
        );

    }

}


function escapeHTML(text) {

    const div =
        document.createElement(
            "div"
        );

    div.textContent =
        text || "";

    return div.innerHTML;

}



document.addEventListener("DOMContentLoaded", function () {

    const menuButton = document.getElementById("mobileMenuBtn");
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("sidebarOverlay");

    if (!menuButton || !sidebar || !overlay) {
        return;
    }


    function openSidebar() {
        sidebar.classList.add("mobile-open");
        overlay.classList.add("active");
        document.body.classList.add("sidebar-open");
    }


    function closeSidebar() {
        sidebar.classList.remove("mobile-open");
        overlay.classList.remove("active");
        document.body.classList.remove("sidebar-open");
    }


    function toggleSidebar() {
        if (sidebar.classList.contains("mobile-open")) {
            closeSidebar();
        } else {
            openSidebar();
        }
    }


    menuButton.addEventListener("click", function () {
        toggleSidebar();
    });


    overlay.addEventListener("click", function () {
        closeSidebar();
    });


    const sidebarLinks = sidebar.querySelectorAll("a");

    sidebarLinks.forEach(function (link) {

        link.addEventListener("click", function () {

            if (window.innerWidth <= 900) {
                closeSidebar();
            }

        });

    });


    document.addEventListener("keydown", function (event) {

        if (event.key === "Escape") {
            closeSidebar();
        }

    });


    window.addEventListener("resize", function () {

        if (window.innerWidth > 900) {
            closeSidebar();
        }

    });

});