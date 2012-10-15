google:
    # values from your app as found on https://code.google.com/apis/console/your_app, tab 'API Access'
    app:
        email:  'XXX@developer.gserviceaccount.com' # %APP_ID%@developer.gserviceaccount.com
        p12_file: 'XXX.p12' # path to the p12 file containing your app's private_key
        p12_secret: 'XXX' # secret on the p12 file

    # about your google apps domain
    domain:
        name: 'XXX' # domain name
        admin_login: 'XXX' # the login of one of the admins

backend:
    root_dir: 'save/' # path to the folder you want to save your files in
    compress: 'True' # optional: controls whether the files are compressed or not
    path_separator: '/' # optional: the path separator on your system (defaults to *nix's '/')