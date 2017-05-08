import React, { Component } from 'react';

// App component - represents the entire app
export default class App extends Component {

  render() {
    return (
       <header>
         <button>Home</button>
         <button>Queue</button>
         <button>Telescope</button>
	 <button>Statistics</button>
       </header>
    );
  }
}