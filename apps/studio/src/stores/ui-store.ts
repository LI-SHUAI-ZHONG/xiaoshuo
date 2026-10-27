"use client";

import { create } from "zustand";

interface UiState {
  commandOpen: boolean;
  detailPanelOpen: boolean;
  draftPanelWidth: number;
  setCommandOpen: (open: boolean) => void;
  setDetailPanelOpen: (open: boolean) => void;
  setDraftPanelWidth: (width: number) => void;
  setSidebarOpen: (open: boolean) => void;
  sidebarOpen: boolean;
}

export const useUiStore = create<UiState>((set) => ({
  commandOpen: false,
  detailPanelOpen: false,
  draftPanelWidth: 420,
  setCommandOpen: (commandOpen) => {
    set({ commandOpen });
  },
  setDetailPanelOpen: (detailPanelOpen) => {
    set({ detailPanelOpen });
  },
  setDraftPanelWidth: (draftPanelWidth) => {
    set({ draftPanelWidth });
  },
  setSidebarOpen: (sidebarOpen) => {
    set({ sidebarOpen });
  },
  sidebarOpen: false,
}));
