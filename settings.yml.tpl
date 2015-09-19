google:
    # values from your app as found on https://console.developers.google.com/project/%your_app_name%/apiui/credential,
    # tab 'APIs & Auth > APIs'
    app:
        # %APP_ID%@developer.gserviceaccount.com
        email:  'XXX@developer.gserviceaccount.com'
        # path to the p12 file containing your app's private_key
        p12_file: 'XXX.p12'
        # secret on the p12 file - it so happens that Google always uses that one
        p12_secret: 'notasecret'

    # about your google apps domain
    domain:
        # domain name
        name: 'XXX'
        # the login of one of the admins
        admin_login: 'XXX'

backend:
    # path to the folder you want to save your files in
    root_dir: 'save/'
    # optional: whether to compress the files or not (defaults to False)
    compression: 'False'
    # optional: compression format, is 'compression' is set to 'True'
    # must be either gz or bz2, defaults to gz
    compression_format: 'gz'
