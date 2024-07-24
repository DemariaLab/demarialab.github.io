function onDOMReady() {
    const underline = document.querySelector('.underline');
    const navItems = document.querySelectorAll('.nav-item');
    const activeItem = document.querySelector('.nav-item.active d');
    const header = document.querySelector("header");

    function updateUnderline(item) {
        if (item) {
            underline.style.transform = 'scaleX(1)';
            const itemRect = item.getBoundingClientRect();
            if (itemRect.width > 0) {
                underline.style.width = itemRect.width + 'px';
                underline.style.left = itemRect.left + 'px';
                underline.style.top = (itemRect.bottom) + 'px';
                underline.style.display = 'block'; // Display the underline once its position is set
            }
        } else {
            underline.style.transform = 'scaleX(0)';
        }
    }

    [...navItems].forEach(item => {
        item.addEventListener('mouseover', function () {
            updateUnderline(item);
        });

        item.addEventListener('mouseout', function () {
            updateUnderline(activeItem);
        });
    });

    requestAnimationFrame(() => {
        if (activeItem) {
            updateUnderline(activeItem);
        }
    });


    // Get the members data from the Liquid script
    const membersData = window.membersData;

    // Split the membersData into an array of member strings
    const membersArray = membersData.split(';').filter(Boolean);

    // Convert the membersArray into an array of objects with last_name_initials and unaccented_name
    const membersList = membersArray.map(member => {
        const [last_name_initials, unaccented_name] = member.split(',');
        return {last_name_initials, unaccented_name};
    });

    // Function to wrap matched text with span
    function wrapText(node, text, className, url) {
        const span = document.createElement('span');
        span.className = className;
        span.textContent = text;

        const link = document.createElement('a');
        link.className = 'no-underline text-current-color';

        if (!url) {
            url = ""
            link.className=link.className+" no-hover"
        } else {
            link.href = '/profiles/member_' + url.replace(/\s+/g, '-') + '.html';
        }

        link.appendChild(span);

        const nodeText = node.textContent;
        const matchIndex = nodeText.indexOf(text);

        if (matchIndex === -1) return;

        const beforeMatch = document.createTextNode(nodeText.slice(0, matchIndex));
        const afterMatch = document.createTextNode(nodeText.slice(matchIndex + text.length));

        const parent = node.parentNode;
        parent.insertBefore(beforeMatch, node);
        parent.insertBefore(link, node);
        parent.insertBefore(afterMatch, node);
        parent.removeChild(node);
    }


    // Get all elements with the .blog.text-content selector
    const blogContent = document.querySelectorAll('.member-highlight-parent');

    // Scan through each .blog.text-content element
    blogContent.forEach(content => {
        membersList.forEach(member => {
            const {last_name_initials, unaccented_name} = member;

            // Create a text node walker
            const walker = document.createTreeWalker(content, NodeFilter.SHOW_TEXT, null, false);
            let node;

            while (node = walker.nextNode()) {
                if (node.textContent.includes(last_name_initials)) {
                    wrapText(node, last_name_initials, 'member-chip', unaccented_name);
                }
                if (node.textContent.includes(unaccented_name)) {
                    wrapText(node, unaccented_name, 'member-chip', unaccented_name);
                }
            }
        });
    });
}


function linkTo_UnCryptMailto(encoded) {
    let decoded = atob(encoded); // Decode the email address
    let linkElement = document.getElementById('emailLink'); // Get the link element by ID
    linkElement.innerHTML = "Email: " + decoded; // Replace the link text with the email address
}

document.addEventListener("DOMContentLoaded", function () {
    onDOMReady();

});



