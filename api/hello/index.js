module.exports = async function (context, req) {
  context.res = {
    status: 200,
    headers: { "Content-Type": "application/json" },
    body: { status: "ok", function: "hello", time: new Date().toISOString() }
  };
};
