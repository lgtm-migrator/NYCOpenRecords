from collections import namedtuple

PermissionPair = namedtuple('Permission', ['value', 'label'])


NONE = 0x000000000

# Request Information Permissions
CHANGE_PRIVACY_TITLE = 0x000000001
CHANGE_PRIVACY_AGENCY_REQUEST_SUMMARY = 0x000000002
EDIT_TITLE = 0x000000004
EDIT_AGENCY_REQUEST_SUMMARY = 0x000000008
VIEW_REQUESTER_INFO = 0x000000010
EDIT_REQUESTER_INFO = 0x000000020
REQUEST_INFO_PERMISSIONS = frozenset((
    CHANGE_PRIVACY_TITLE,
    CHANGE_PRIVACY_AGENCY_REQUEST_SUMMARY,
    EDIT_TITLE,
    EDIT_AGENCY_REQUEST_SUMMARY,
    EDIT_REQUESTER_INFO
))

# Response Permissions
ADD_FILE = 0x000000040
ADD_LINK = 0x000000080
ADD_OFFLINE_INSTRUCTIONS = 0x000000100
ADD_NOTE = 0x000000200
GENERATE_LETTER = 0x100000000
ADD_RESPONSE_PERMISSIONS = frozenset((
    ADD_FILE,
    ADD_LINK,
    ADD_OFFLINE_INSTRUCTIONS,
    ADD_NOTE,
    GENERATE_LETTER
))
EDIT_FILE = 0x000000400
EDIT_FILE_PRIVACY = 0x000000800
EDIT_LINK = 0x0000001000
EDIT_LINK_PRIVACY = 0x000002000
EDIT_OFFLINE_INSTRUCTIONS = 0x000004000
EDIT_OFFLINE_INSTRUCTIONS_PRIVACY = 0x000008000
EDIT_NOTE = 0x000010000
EDIT_NOTE_PRIVACY = 0x000020000
EDIT_RESPONSE_PERMISSIONS = frozenset((
    EDIT_FILE,
    EDIT_FILE_PRIVACY,
    EDIT_LINK,
    EDIT_LINK_PRIVACY,
    EDIT_OFFLINE_INSTRUCTIONS,
    EDIT_OFFLINE_INSTRUCTIONS_PRIVACY,
    EDIT_NOTE,
    EDIT_NOTE_PRIVACY
))
DELETE_FILE = 0x000040000
DELETE_LINK = 0x000080000
DELETE_OFFLINE_INSTRUCTIONS = 0x000100000
DELETE_NOTE = 0x000200000
DELETE_RESPONSE_PERMISSIONS = frozenset((
    DELETE_FILE,
    DELETE_LINK,
    DELETE_OFFLINE_INSTRUCTIONS,
    DELETE_NOTE,
))
RESPONSE_PERMISSIONS = frozenset((
    ADD_FILE,
    ADD_LINK,
    ADD_OFFLINE_INSTRUCTIONS,
    ADD_NOTE,
    GENERATE_LETTER,
    EDIT_FILE,
    EDIT_FILE_PRIVACY,
    EDIT_LINK,
    EDIT_LINK_PRIVACY,
    EDIT_OFFLINE_INSTRUCTIONS,
    EDIT_OFFLINE_INSTRUCTIONS_PRIVACY,
    EDIT_NOTE,
    EDIT_NOTE_PRIVACY,
    DELETE_FILE,
    DELETE_LINK,
    DELETE_OFFLINE_INSTRUCTIONS,
    DELETE_NOTE,
))

# Determination Permissions
ACKNOWLEDGE = 0x000400000
DENY = 0x000800000
EXTEND = 0x001000000
CLOSE = 0x002000000
RE_OPEN = 0x004000000
DETERMINATION_PERMISSIONS = frozenset((
    ACKNOWLEDGE,
    DENY,
    EXTEND,
    CLOSE,
    RE_OPEN,
))

# User Management Functionality
ADD_USER_TO_REQUEST = 0x008000000
REMOVE_USER_FROM_REQUEST = 0x010000000
EDIT_USER_REQUEST_PERMISSIONS = 0x020000000
ADD_USER_TO_AGENCY = 0x040000000
REMOVE_USER_FROM_AGENCY = 0x080000000
CHANGE_USER_ADMIN_PRIVILEGE = 0x100000000
USER_MANAGEMENT_PERMISSIONS = frozenset((
    ADD_USER_TO_REQUEST,
    REMOVE_USER_FROM_REQUEST,
    EDIT_USER_REQUEST_PERMISSIONS,
    ADD_USER_TO_AGENCY,
    REMOVE_USER_FROM_AGENCY,
    CHANGE_USER_ADMIN_PRIVILEGE,
))

ALL = [
    PermissionPair(ACKNOWLEDGE, "Acknowledge Request"),
    PermissionPair(DENY, "Deny Request"),
    PermissionPair(EXTEND, "Extend Request"),
    PermissionPair(CLOSE, "Close Request"),
    PermissionPair(RE_OPEN, "Re-Open Request"),
    PermissionPair(CHANGE_PRIVACY_TITLE, "Change Title Privacy"),
    PermissionPair(CHANGE_PRIVACY_AGENCY_REQUEST_SUMMARY, "Change Agency Request Summary Privacy"),
    PermissionPair(EDIT_TITLE, "Edit Title"),
    PermissionPair(EDIT_AGENCY_REQUEST_SUMMARY, "Edit Agency Request Summary"),
    PermissionPair(ADD_FILE, "Add Files"),
    PermissionPair(ADD_LINK, "Add Links"),
    PermissionPair(ADD_OFFLINE_INSTRUCTIONS, "Add Offline Instructions"),
    PermissionPair(ADD_NOTE, "Add Notes"),
    PermissionPair(GENERATE_LETTER, "Generate Letters"),
    PermissionPair(EDIT_FILE, "Edit Files"),
    PermissionPair(EDIT_FILE_PRIVACY, "Change File Privacy"),
    PermissionPair(EDIT_LINK, "Edit Links"),
    PermissionPair(EDIT_LINK_PRIVACY, "Change Link Privacy"),
    PermissionPair(EDIT_OFFLINE_INSTRUCTIONS, "Edit Offline Instructions"),
    PermissionPair(EDIT_OFFLINE_INSTRUCTIONS_PRIVACY, "Change Offline Instructions Privacy"),
    PermissionPair(EDIT_NOTE, "Edit Notes"),
    PermissionPair(EDIT_NOTE_PRIVACY, "Change Note Privacy"),
    PermissionPair(DELETE_FILE, "Delete File"),
    PermissionPair(DELETE_LINK, "Delete Link"),
    PermissionPair(DELETE_OFFLINE_INSTRUCTIONS, "Delete Offline Instructions"),
    PermissionPair(DELETE_NOTE, "Delete Note"),
    PermissionPair(ADD_USER_TO_REQUEST, "Add User"),
    PermissionPair(REMOVE_USER_FROM_REQUEST, "Remove User"),
    PermissionPair(EDIT_USER_REQUEST_PERMISSIONS, "Edit User Request Permissions"),
    PermissionPair(EDIT_REQUESTER_INFO, "Edit Requester Information")
]
