Brive, the Google Apps Domains' Drive Backup application
=====

Brive allows you to backup all the Google Drive documents accessible by all your Google Apps domain's users.

Each time it is run, it creates a full snapshot of your users' Drive accounts' contents.

You can also use it to retrieve only the docs of some specific users, and/or to retrieve only some specific documents. Additionally, you can choose the formats you prefer to have your documents exported in.

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

_Note that Google frequently changes their UI. I try to keep the following instructions up-to-date, but it's entirely possible that they may be silghtly outdated. Please let me know if that's the case._

We will now create your private Google App application : log into your Google Apps domain control panel as an administrator (https://admin.google.com/), then:
<ol>
<li> Create an API project in the Google APIs Console: go to https://console.developers.google.com/ and click 'Create an empry project' - choose any name you want </li>
<li> It might take some time for your project to be created </li>
<li> When it is, select the 'APIs & auth > APIs' tab in your API project, and enable the 'Drive API' and the 'Admin SDK' API </li>
<li> Select the 'APIs & auth > Credentials' tab in your API project, and click on 'Add credentials'. In the drop down menu that appears, select 'Service account' </li>
<li> On the next screen, select 'P12' instead of 'JSON' </li>
<li> Download the P12 file, and report the path to it in the 'google > app > p12_file' entry of your `settings.yml` file </li>
<li> Report your private key's password (should be 'notascret') to the 'google > app > p12_secret' entry of your `settings.yml` file </li>
<li> In the 'Service accounts' section now displayed, please report the 'Email address' value (should be of the form %name%-%some_id%@%project%-%some_id%.iam.gserviceaccount.com) to the 'google > app > email' entry of your `settings.yml` file </li>
<li> To get your client ID go to generated credentials 'API Manager > Credentials > Manage Service Account' and select edit. 'Check box Enable Google Apps Domain-wide Delegation', click save and copy generated client ID. </li>

Now we need to grant the necessary access rights to this application on your domain:
<ol>
<li> Open your domain's control panel (https://admin.google.com/) </li>
<li> Click 'Security'. In the new screen that appears, click 'Show more', then 'Advanced settings', then 'Manage API client access' in the 'Authentication' section </li>
<li> In the 'Client Name' field, report the client ID value you saved from step 9 above </li>
<li> In the 'One or More API Scopes' field, please copy and paste:<br/>
<code>https://www.googleapis.com/auth/admin.directory.user.readonly,https://www.googleapis.com/auth/drive.readonly</code><br/>
(the first one allows your application to get the list of all users on your domain, the second one to fetch the data from your users' Drive accounts), then click 'Authorize' </li>
</ol>

<b>Optional:</b> feel free to edit the three 'backend' entries in your `settings.yml` file; please read the comments there.

<h1>How to use</h1>

When in your Brive directory, just execute the `brive.py` file. See all the possible flags by running `brive.py --help`.

The exit code will be 0 if and only if the backup was successful. If it wasn't, you should get an explanatory message in your `stderr` stream.

<h1>Security considerations</h1>

You're responsible for keeping your application's credentials safe. Anyone with your certificate file will be able to get data on all users on your domain, and see all the data they keep on Google Drive.

Note that if your certificate file gets stolen, you can always revoke your app's access to your domain, thus preventing any further abuse.

<h1>Bugs and suggestions</h1>

Please feel free to report any bug/suggestion, or to ask any question you might have at `brive.x8wk at gmail dot com`.
