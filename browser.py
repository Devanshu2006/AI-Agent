from playwright.sync_api import sync_playwright


def inspect_website(url: str):

    with sync_playwright() as p:

        browser = p.chromium.launch(
            headless=False
        )

        page = browser.new_page(
            viewport={
                "width": 1440,
                "height": 900
            }
        )

        print(
            f"\n[Browser] Opening: {url}"
        )

        page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=60000
        )

        page.wait_for_timeout(
            2000
        )

        title = page.title()

        current_url = page.url

        # ----------------------------------------------------
        # BODY TEXT
        # ----------------------------------------------------

        try:

            page_text = page.locator(
                "body"
            ).inner_text()

        except Exception:

            page_text = ""

        page_text = page_text[:15000]

        # ----------------------------------------------------
        # INTERACTIVE ELEMENTS
        # ----------------------------------------------------

        elements = page.locator(
            "input, button, a, select, textarea"
        ).evaluate_all(
            """
            elements => elements.map((el, index) => ({
                index: index,
                tag: el.tagName,
                text: (el.innerText || '').trim(),
                type: el.getAttribute('type'),
                name: el.getAttribute('name'),
                id: el.getAttribute('id'),
                placeholder: el.getAttribute('placeholder'),
                aria_label: el.getAttribute('aria-label'),
                role: el.getAttribute('role'),
                href: el.getAttribute('href'),
                value: el.getAttribute('value'),
                disabled: el.disabled,
                required: el.required
            }))
            """
        )

        # ----------------------------------------------------
        # FORMS
        # ----------------------------------------------------

        forms = page.locator(
            "form"
        ).evaluate_all(
            """
            forms => forms.map((form, index) => ({
                index: index,
                action: form.getAttribute('action'),
                method: form.getAttribute('method'),
                text: (form.innerText || '').trim()
            }))
            """
        )

        # ----------------------------------------------------
        # HEADINGS
        # ----------------------------------------------------

        headings = page.locator(
            "h1, h2, h3"
        ).evaluate_all(
            """
            elements => elements.map(el => ({
                tag: el.tagName,
                text: (el.innerText || '').trim()
            }))
            """
        )

        # ----------------------------------------------------
        # LINKS
        # ----------------------------------------------------

        links = page.locator(
            "a"
        ).evaluate_all(
            """
            elements => elements.map(el => ({
                text: (el.innerText || '').trim(),
                href: el.getAttribute('href')
            }))
            """
        )

        # ----------------------------------------------------
        # SCREENSHOT
        # ----------------------------------------------------

        page.screenshot(
            path="website.png",
            full_page=True
        )

        browser.close()

        return {
            "url": current_url,
            "title": title,
            "page_text": page_text,
            "elements": elements,
            "forms": forms,
            "headings": headings,
            "links": links
        }