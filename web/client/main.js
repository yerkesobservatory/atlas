// import routing
import '../imports/router.js';

import { Template } from 'meteor/templating';

import './main.html';

// navbar
import '../imports/ui/navigation.js';

// home
import '../imports/ui/home.js';

// telescope
import '../imports/ui/telescopes.js';

// profile
import '../imports/ui/profile.js';

// observation list
import '../imports/ui/observations.js';

// session list
import '../imports/ui/sessions.js';

// programs
import '../imports/ui/programs.js';

// auth
import '../imports/auth/login.js';
import '../imports/auth/reset-password.js';

// gui
import '../imports/ui/control.js';

// ==== admin === //
import '../imports/admin/admin.js';
import '../imports/admin/groups.js';

// deny client side updates to users
Meteor.users.deny({
    update() { return true; }
});




