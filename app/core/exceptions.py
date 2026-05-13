class NotFoundException(Exception):
    def __init__(self,detail: str="The requested resource was not found"):   #detail=optional
        self.status_code=404
        self.detail=detail

class PermissionDeniedException(Exception):
    def __init__(self,detail:str="You do not have permission to perform this action"):
        self.status_code=403
        self.detail=detail

class AlreadyExistsException(Exception):
    def __init__(self,detail:str="The resource already exists"):
        self.status_code=400
        self.detail=detail

class UnauthorizedException(Exception):
    def __init__(self,detail:str="You are not authorized to perform this action"):
        self.status_code=401
        self.detail=detail

class InvalidCredentialsException(Exception):
    def __init__(self,detail:str="Invalid credentials"):
        self.status_code=401
        self.detail=detail

class SessionException(Exception):
    def __init__(self,detail:str="Session expired"):
        self.status_code=401
        self.detail=detail

class MissingCredentialException(Exception):
    def __init__(self,detail:str="Missing credentials"):
        self.status_code=400
        self.detail=detail

class ValidationException(Exception):
    def __init__(self,detail:str="Invalid input"):
        self.status_code=400
        self.detail=detail