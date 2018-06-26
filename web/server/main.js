import { Meteor } from 'meteor/meteor';
import { Random } from 'meteor/random';
import { Programs } from '../imports/api/programs.js';

// import routing
import '../imports/router.js';

// import API code
import '../imports/api/observations.js';
import '../imports/api/sessions.js';
import '../imports/api/programs.js';
import '../imports/api/telescopes.js';
import '../imports/api/users.js';
import '../imports/api/groups.js';
import '../imports/api/announcements.js';
//somewhere in both (client and  server) 
import {SimpleChat} from 'meteor/cesarve:simple-chat/config'

Meteor.startup(() => {
    // code to run on server at startup

    // there are no users, this is our FIRST startup
    if ( !Meteor.users.findOne()) {

        // create a user
        const password = Random.id();
        const id = Accounts.createUser({
            email: 'newaccount@admin.com',
            password: password
        });

        // make the user an admin
        Roles.addUsersToRoles(id, 'admin');

        // print the password
        console.log("Created new account with password: "+password);

	// function to insert a program
        function insertProgram(name, executor) {
            Programs.insert({
                name: name,
                executor: executor,
                owner: null,
                completed: false,
                sessions: [],
                observations: [],
                createdAt: new Date()
            });
        }

        // creating public programs
        insertProgram('General', 'general');
        insertProgram('Asteroids', 'asteroid');
        insertProgram('Variable Stars', 'variable');
        insertProgram('Solar System', 'solarsystem');
    }
});

(function () {
    "use strict";

    Accounts.urls.resetPassword = function (token) {
        return Meteor.absoluteUrl('reset/' + token);
    };

    Accounts.urls.enrollAccount = function (token) {
        return Meteor.absoluteUrl('reset/' + token);
    };

    Accounts.emailTemplates.from = 'Stone Edge Observatory <sirius.stonedgeobservatory@gmail.com>';
    Accounts.emailTemplates.siteName = 'Stone Edge Observatory';

    // setup enrollment email
    Accounts.emailTemplates.enrollAccount.text = (user, url) => {
        return 'Welcome to Atlas @ Stone Edge Observatory!\n\n'
            + 'To activate your account, please click the link below:\n\n'
            + url;
    };
    Accounts.emailTemplates.enrollAccount.subject = (user, url) => {
        return 'Your new Stone Edge Observatory account';
    };

    // configure password reset message
    Accounts.emailTemplates.resetPassword.text = (user, url) => {
        return 'Hello from Atlas @ Stone Edge Observatory!\n\n'
            + 'Your password has been successfully reset; to set your'
            + ' new password, please click the link below. \n\n'
            + url;
    };
    Accounts.emailTemplates.resetPassword.subject = (user, url) => {
        return 'Resetting your password for Atlas @ Stone Edge Observatory';
    };

})();




SimpleChat.configure ({
    texts:{
        loadMore: 'Load More',
        placeholder: 'Type message ...',
        button: 'send',
        join: 'joined the',
        left: 'left',
        room: 'room at'

    },
    limit: 10,
    beep: true, 
    showViewed: true,
    showReceived: true,
    showJoined: true,
    /*
    publishChats: function(roomId, limi){ //server
       //here the context is the same for a Publications, that mean you have access to this.userId who are asking for subscribe.
       // for example
       //return isLoggedAndHasAccessToSeeMessage(this.userId)
    },
    allow: function(message, roomId, username, avatar, name){
       //here the context is the same for a Methods, thats mean you hace access to this.userId also
       // for example
       //return isLoggedAndHasAccessSendMessages(this.userId)
        return true
    },
    onNewMessage:function(msg){  //both
    },
    onReceiveMessage:function(id, message, room){ //server
        
    },
    onJoin:function(roomId, username, name,date){  //server
    },
    onLeft:function(roomId, username, name,date) { //server
    },
    height: '300px', // Configure the height of the chat
    inputTemplate: 'SimpleChatInput', // In case you want to overwrite the template
    loadMoreTemplate: 'LoadMore', // In case you want to overwrite the template*/
});
