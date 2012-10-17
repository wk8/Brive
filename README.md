Brive, the Google Apps Domains' Drive Backup application
=====

Brive allows you to backup all the Google Drive documents accessible by all your Google Apps domain's users.

Each time it is run, it creates a full snapshot of your users' Drive accounts' contents.

<h1>Installation</h1>

<h2>Local installation</h2>

Clone the source code:

`git clone https://github.com/x8wk/Brive.git`

Then `cd` into the new directory, and download the dependencies:

`sudo python setup.py install -n`

<h2>Setting up your Google API application</h2>

Still in the Brive directory,

`cp settings.yml.tpl settings.yml`

then open `settings.yml` with your favorite text editor. In that file, please fill in the two 'google > domain' entries (your domain name, and the login of one of your administator users).

We will now create your private Google App application : log into your Google Apps domain control panel as an administrator, then:
<ol>
<li> Create an API project in the Google APIs Console: https://code.google.com/apis/console/b/0/ </li>
<li> Select the 'Services' tab in your API project, and enable the Drive API </li>
<li> Select the 'API Access' tab in your API project, and click 'Create an OAuth 2.0 client ID' </li>
<li> In the 'Branding Information section', provide a name for your application (whatever you want), and click 'Next'. Providing a product logo is optional. </li>
<li> In the Client ID Settings section, select 'Service account' for the 'Application type', then click 'Create client ID' </li>
<li> Report your private key's password (should be 'notascret') to the 'google > app > p12_secret' entry of your `settings.yml` file </li>
<li> Click 'Download private key', save the file in Brive's directory, and report the path to it in the 'google > app > p12_file' entry of your `settings.yml` file </li>
<li> You can now close the 'Public-Private Key Pair Generated' popup </li>
<li> In the 'Service account' section now displayed, please report the 'Email address' value (should be of the form %some_id%@334156113202@developer.gserviceaccount.com) to the 'google > app > email' entry of your `settings.yml` file </li>
<li> Still in the 'Service account' section, save for later the 'Client ID' value (should be of the form %same_id_as_in_email_address%334156113202.apps.googleusercontent.com) </li>
</ol>

Now we need to grant the necessary access rights to this application on your domain:
<ol>
<li> Open your domain's control panel (https://www.google.com/a/cpanel/%your-domain-name%) </li>
<li> Go to the 'Advanced tools' tab, and click the 'Manage third parties party OAuth Client access' link in the 'Authentication' section </li>
<li> In the 'Client Name' field, report the 'Client ID' value you saved from step 10 above </li>
<li> In the 'One or More API Scopes', please copy and paste:<br/>
<code>https://apps-apis.google.com/a/feeds/user/,https://www.googleapis.com/auth/drive.readonly</code><br/>
(the first one allows your application to get the list of all users on your domain, the second one to fetch the data from your users' Drive accounts) </li>
</ol>

<b>Optional:</b> feel free to edit the three 'backend' entries in your `settings.yml` file; please read the comments there.

<h1>How to use</h1>

When in your Brive directory, just execute the `brive.py` file. Additionally, you can pass it a `-v` flag to run it in verbose mode, or `-d` to run it in Log.debug mode (more output).

The exit code will be 0 if and only if the backup was successful. If it wasn't, you should get an explanatory message in your `stderr` stream.

<h1>Security considerations</h1>

You're responsible for keeping your application's credentials safe. Anyone with your certificate file will be able to get data on all users on your domain, and see all the data they keep on Google Drive.

Note that if your certificate file gets stolen, you can always revoke your app's access to your domain, thus preventing any further abuse.

<h1>Bugs and suggestions</h1>

Please feel free to report any bug/suggestion, or to ask any question you might have at `brive.x8wk at gmail dot com`.
