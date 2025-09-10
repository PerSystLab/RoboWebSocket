const WebSocket = require("ws");

const PORT = 8080;
const wss = new WebSocket.Server({ port: PORT });

let clients = [];

wss.on("connection", (ws) => {
  clients.push(ws);

  ws.on("message", (message) => {
    const parsedMessage = message.toString();
    console.log("Received:", parsedMessage);

    clients.forEach((client) => {
      if (client !== ws && client.readyState === WebSocket.OPEN) {
        client.send(parsedMessage);
      }
    });
  });

  ws.on("close", () => {
    clients = clients.filter((client) => client !== ws);
  });

  console.log("New client connected");
});

console.log(`Signaling server is running on ws://localhost:${PORT}`);
