function handler(event) {
    var request = event.request;
    var uri = request.uri;
    
    // Check if the URI is for a file (has a file extension)
    if (uri.includes('.')) {
        // Return the request unchanged for files
        return request;
    }
    
    // Check if the URI ends with a slash
    if (uri.endsWith('/')) {
        // Append index.html to directory requests
        request.uri = uri + 'index.html';
    } else {
        // For SPA routing, redirect all non-file requests to index.html
        // but preserve the original URI for client-side routing
        if (uri !== '/' && uri !== '/index.html') {
            request.uri = '/index.html';
        }
    }
    
    return request;
}