/* eslint-disable react-refresh/only-export-components -- shared context + hook */
import React, { createContext, useContext } from 'react';

const AutomatorUserContext = createContext(null);

export function AutomatorUserProvider({ user, children }) {
  return (
    <AutomatorUserContext.Provider value={user}>
      {children}
    </AutomatorUserContext.Provider>
  );
}

export function useAutomatorUser() {
  const user = useContext(AutomatorUserContext);
  if (!user) {
    throw new Error('useAutomatorUser must be used within AutomatorUserProvider');
  }
  return user;
}
