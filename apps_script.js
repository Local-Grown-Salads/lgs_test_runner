/**
 * Google Apps Script - Add this to your Google Sheet
 *
 * To install:
 * 1. In Google Sheets, go to Extensions → Apps Script
 * 2. Delete any existing code and paste this entire file
 * 3. Save (Ctrl+S)
 * 4. Reload your spreadsheet
 * 5. You'll see a new "Test Runner" menu
 */

// CONFIGURE THIS: Your server URL (use ngrok for local dev)
const SERVER_URL = "http://localhost:8000";

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu("🧪 Test Runner")
    .addItem("Run Tests", "runTests")
    .addToUi();
}

function runTests() {
  const ui = SpreadsheetApp.getUi();
  const sheet = SpreadsheetApp.getActiveSpreadsheet();
  const spreadsheetId = sheet.getId();
  const worksheetName = sheet.getActiveSheet().getName();

  ui.alert("Running tests...", "Please wait while tests are executed.", ui.ButtonSet.OK);

  try {
    const response = UrlFetchApp.fetch(SERVER_URL + "/run", {
      method: "post",
      contentType: "application/json",
      payload: JSON.stringify({
        spreadsheet_id: spreadsheetId,
        worksheet_name: worksheetName,
      }),
      muteHttpExceptions: true,
    });

    const status = response.getResponseCode();
    const body = response.getContentText();

    if (status === 200) {
      const result = JSON.parse(body);
      ui.alert(
        "Tests Complete",
        `✓ Passed: ${result.passed}\n✗ Failed: ${result.failed}\n\nTotal: ${result.total}`,
        ui.ButtonSet.OK
      );
    } else {
      ui.alert("Error", `Server returned ${status}: ${body}`, ui.ButtonSet.OK);
    }
  } catch (error) {
    ui.alert(
      "Connection Error",
      `Could not reach server at ${SERVER_URL}\n\nMake sure the server is running:\nuv run python server.py\n\nError: ${error.message}`,
      ui.ButtonSet.OK
    );
  }
}
