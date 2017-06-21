# CEA
_CEA_ (working title) is a tool for [Sudbury schools](https://en.wikipedia.org/wiki/Sudbury_school) to manage their internal judicial system. It was made for Belgium's [Ecole Autonome](http://www.ecole-autonome.be) and every Sudbury school being unique, it might require some tweaking for individual schools.

## Installation
* Clone the GitHub repository : `git clone https://github.com/Zinston/cea.git`
* [Install](https://cloud.google.com/sdk/docs/) GCloud
* [Make](https://console.cloud.google.com) a Google App Engine account and create a new project
* Customize (changing the logo in the navbar `src/templates/cea-base.html` is probably where you want to start)
* [Deploy](https://cloud.google.com/sdk/gcloud/reference/app/deploy) to Google App Engine when you're satisfied : `gcloud deploy --version 1`

## Usage
* Judicial Committe Clerks at a Sudbury School open up this app when they prepare the JC and encode the numbers of all new complaints (they can also take some notes in the "report" section) to make them appear in the unfinished business.
* When JC begins, they follow their due process on the app.
* They can use the app the see the personal history of one particular School Meeting member with a rule or check how a specific rule has been interpreted before (both through the _search_ feature).

## Features
* See the last ten finished complaints on the front page
* Add School Meeting members (using the _user_ icon on the top right)
* Add rules to your lawbook (using the _law_ icon on the top right)
* Create new complaints to treat (using the _+_ icon in the middle)
  * In phase 1 (report): enter your complaint number and report
  * In phase 2 (inculpation): enter one or several inculpations with the rule(s) allegedly infringed, plea and sentence
* Check and edit unfinished business (using the _loading_ icon in the middle)
* Search through complaints in your database (using the _search_ icon in the middle)
  * Search by number
  * Search by guilty plea or verdict
  * Search by rule infringed (also prints out the rule itself for reference)
  * Cross-search by guily plea/verdic and rule infringed
  * Print out the list of complaints to give to the School Meeting Secretary for examination at the next School Meeting (then cross out all complaints that have already been presented)

## History
_CEA_ was developed by one of the founders of [Ecole Autonome](http://www.ecole-autonome.be), who learned to program as he went, to automize some of his work as both Judicial Committee Clerk and School Meeting Secretary. It was used throughout the school's one-year existence.

## License
_CEA_ is released under the [GNU General Public License v3.0](cea/LICENSE.txt).
