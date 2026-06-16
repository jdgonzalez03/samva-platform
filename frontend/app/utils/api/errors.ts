export class NotFoundError extends Error {
  statusCode = 404
  statusMessage: string;

  constructor(statusMessage = "Not Found") {
    super(statusMessage);
    this.name = "NotFoundError";
    this.statusMessage = statusMessage;
  }
}


export class RefreshTokenError extends Error {
  statusCode = 401
  statusMessage: string;

  constructor(statusMessage = "Refresh Token Error") {
    super(statusMessage);
    this.name = "RefreshTokenError";
    this.statusMessage = statusMessage;
  }
}
