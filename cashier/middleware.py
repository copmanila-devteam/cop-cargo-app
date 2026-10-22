from django.shortcuts import render


class HideJsonFromBrowserMiddleware:
    """Keep the JSON API out of the address bar.

    The pages load their data with fetch(), so a JSON response opened directly as a page
    (typing /api/list/ or /cashier/5/details/ into the browser) gets the 404 page instead.
    Browsers mark a page load with Sec-Fetch-Mode: navigate; fetch() calls send cors/same-origin.

    This only stops casual viewing and caching. It is NOT access control: the data a page
    fetches is still visible to that signed-in user in DevTools, so every JSON view must
    still check the user's role and return only what that role needs.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if not response.get('Content-Type', '').startswith('application/json'):
            return response

        # Personal data: never keep it in the browser cache or a shared proxy
        response['Cache-Control'] = 'no-store, private'

        # Only GET/HEAD: a POST already ran its changes, and those are CSRF-protected anyway
        is_page_load = (
            request.headers.get('Sec-Fetch-Mode') == 'navigate'
            or request.headers.get('Sec-Fetch-Dest') == 'document'
        )
        if request.method in ('GET', 'HEAD') and is_page_load:
            return render(request, 'error_pages/404_page.html', status=404)

        return response
