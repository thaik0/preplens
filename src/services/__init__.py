"""Reusable PrepLens workflow services.

CLI commands and a future API backend should call these services instead of
duplicating orchestration logic. Lower-level modules still own storage,
retrieval, generation, logging, and evaluation details.
"""
