from django.http import HttpResponse

def direct_index_view(request):
    """Serve the index page directly as HTML content"""
    html = """<!DOCTYPE html>
<html lang="uk">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Telegram Parser | Railway Deployment</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.2/css/all.min.css">
    <style>
        body {
            background-color: #f8f9fc;
            font-family: 'Nunito', sans-serif;
            min-height: 100vh;
            display: flex;
            flex-direction: column;
        }
        
        .navbar {
            background: linear-gradient(to right, #4e73df, #8e54e9);
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }
        
        .navbar-brand {
            font-weight: 700;
            font-size: 1.5rem;
        }
        
        .main-content {
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .bot-status-card {
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
            transition: all 0.3s ease;
            max-width: 600px;
            width: 100%;
        }
        
        .bot-status-card:hover {
            transform: translateY(-5px);
            box-shadow: 0 15px 30px rgba(0, 0, 0, 0.2);
        }
        
        .status-indicator {
            width: 20px;
            height: 20px;
            border-radius: 50%;
            background-color: #2ecc71;
            display: inline-block;
            margin-right: 8px;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0% {
                box-shadow: 0 0 0 0 rgba(46, 204, 113, 0.4);
            }
            70% {
                box-shadow: 0 0 0 10px rgba(46, 204, 113, 0);
            }
            100% {
                box-shadow: 0 0 0 0 rgba(46, 204, 113, 0);
            }
        }
        
        .footer {
            background-color: #343a40;
            color: rgba(255, 255, 255, 0.8);
            padding: 15px 0;
        }
    </style>
</head>
<body>
    <!-- Navigation -->
    <nav class="navbar navbar-expand-lg navbar-dark">
        <div class="container">
            <a class="navbar-brand" href="/">
                <i class="fas fa-robot me-2"></i>
                Telegram Parser
            </a>
            <div class="ms-auto">
                <a href="/admin_panel/" class="btn btn-light btn-sm">
                    <i class="fas fa-tachometer-alt me-1"></i> Admin Panel
                </a>
            </div>
        </div>
    </nav>

    <!-- Main Content -->
    <div class="main-content">
        <div class="container">
            <div class="row justify-content-center">
                <div class="col-md-10">
                    <div class="bot-status-card">
                        <div class="card-body text-center p-5">
                            <div class="mb-4">
                                <span class="status-indicator"></span>
                                <span class="badge bg-success fs-5">Online</span>
                            </div>
                            <h1 class="display-4 mb-4">Telegram bot is running</h1>
                            <p class="lead mb-4">The Telegram parsing service is active and successfully monitoring channels.</p>
                            <div class="d-grid gap-3 d-sm-flex justify-content-sm-center">
                                <a href="/admin_panel/" class="btn btn-primary btn-lg px-4 gap-3">
                                    <i class="fas fa-tachometer-alt me-2"></i> Go to Admin Panel
                                </a>
                                <a href="https://t.me/chan_parsing_mon_bot" class="btn btn-info btn-lg px-4">
                                    <i class="fab fa-telegram me-2"></i> Open Telegram Bot
                                </a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Footer -->
    <footer class="footer text-center">
        <div class="container">
            <p class="mb-0">&copy; 2025 Telegram Parser. All rights reserved.</p>
        </div>
    </footer>

    <script src="https://code.jquery.com/jquery-3.7.1.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
</body>
</html>"""
    return HttpResponse(html, content_type='text/html')
