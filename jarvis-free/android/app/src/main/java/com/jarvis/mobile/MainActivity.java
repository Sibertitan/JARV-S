package com.jarvis.mobile;

import android.app.Activity;
import android.graphics.Color;
import android.graphics.Typeface;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.view.inputmethod.InputMethodManager;
import android.content.Context;
import android.content.SharedPreferences;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public final class MainActivity extends Activity {
    private static final String PREFS = "jarvis_mobile";
    private static final int INK = Color.rgb(24, 35, 40);
    private static final int MUTED = Color.rgb(95, 108, 113);
    private static final int ACCENT = Color.rgb(0, 121, 107);

    private final ExecutorService network = Executors.newSingleThreadExecutor();
    private EditText address;
    private EditText accessCode;
    private EditText message;
    private TextView status;
    private TextView transcript;
    private Button connectButton;
    private Button sendButton;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        buildUi();
        SharedPreferences prefs = getSharedPreferences(PREFS, MODE_PRIVATE);
        address.setText(prefs.getString("address", ""));
        accessCode.setText(prefs.getString("token", ""));
        setStatus("Bağlantı bekleniyor");
    }

    private void buildUi() {
        LinearLayout page = new LinearLayout(this);
        page.setOrientation(LinearLayout.VERTICAL);
        page.setPadding(dp(18), dp(18), dp(18), dp(12));
        page.setBackgroundColor(Color.rgb(246, 248, 247));

        TextView title = new TextView(this);
        title.setText("JARVIS");
        title.setTextColor(INK);
        title.setTextSize(24);
        title.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        page.addView(title);

        status = new TextView(this);
        status.setTextColor(MUTED);
        status.setTextSize(14);
        status.setPadding(0, dp(4), 0, dp(12));
        page.addView(status);

        address = field("Jarvis bilgisayarının adresi (ör. http://192.168.1.5:8765)");
        page.addView(address, matchWrap());
        accessCode = field("Jarvis uygulamasında görünen bağlantı kodu");
        accessCode.setInputType(129);
        page.addView(accessCode, matchWrap());

        connectButton = button("Bağlan");
        connectButton.setOnClickListener(v -> connect());
        page.addView(connectButton, matchWrap());

        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        transcript = new TextView(this);
        transcript.setTextColor(INK);
        transcript.setTextSize(16);
        transcript.setTextIsSelectable(true);
        transcript.setPadding(dp(12), dp(12), dp(12), dp(12));
        transcript.setBackgroundColor(Color.WHITE);
        scroll.addView(transcript);
        LinearLayout.LayoutParams scrollParams = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1f);
        scrollParams.topMargin = dp(12);
        page.addView(scroll, scrollParams);

        LinearLayout composer = new LinearLayout(this);
        composer.setOrientation(LinearLayout.HORIZONTAL);
        composer.setGravity(Gravity.CENTER_VERTICAL);
        message = field("Jarvis'e yaz...");
        composer.addView(message, new LinearLayout.LayoutParams(0, dp(52), 1f));
        sendButton = button("Gönder");
        LinearLayout.LayoutParams sendParams = new LinearLayout.LayoutParams(dp(92), dp(52));
        sendParams.leftMargin = dp(8);
        composer.addView(sendButton, sendParams);
        sendButton.setOnClickListener(v -> sendMessage());
        LinearLayout.LayoutParams composerParams = matchWrap();
        composerParams.topMargin = dp(10);
        page.addView(composer, composerParams);

        setContentView(page);
    }

    private EditText field(String hint) {
        EditText input = new EditText(this);
        input.setSingleLine(true);
        input.setHint(hint);
        input.setTextColor(INK);
        input.setHintTextColor(MUTED);
        input.setTextSize(15);
        input.setPadding(dp(12), 0, dp(12), 0);
        return input;
    }

    private Button button(String text) {
        Button button = new Button(this);
        button.setText(text);
        button.setTextColor(Color.WHITE);
        button.setBackgroundTintList(android.content.res.ColorStateList.valueOf(ACCENT));
        return button;
    }

    private LinearLayout.LayoutParams matchWrap() {
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        params.bottomMargin = dp(6);
        return params;
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private void connect() {
        persistConnection();
        String base = address.getText().toString().trim();
        String token = accessCode.getText().toString().trim();
        setStatus("Bağlanıyor…");
        connectButton.setEnabled(false);
        network.execute(() -> {
            try {
                JSONObject response = post("/ping", null, base, token);
                runOnUiThread(() -> {
                    setStatus("Bağlı");
                    append("JARVIS", response.optString("reply", "Bağlantı kuruldu."));
                });
            } catch (Exception e) {
                runOnUiThread(() -> setStatus(errorText(e)));
            } finally {
                runOnUiThread(() -> connectButton.setEnabled(true));
            }
        });
    }

    private void sendMessage() {
        String text = message.getText().toString().trim();
        if (text.isEmpty()) return;
        if (text.length() > 10000) {
            setStatus("Mesaj çok uzun (en fazla 10.000 karakter).");
            return;
        }
        persistConnection();
        String base = address.getText().toString().trim();
        String token = accessCode.getText().toString().trim();
        append("Sen", text);
        message.setText("");
        sendButton.setEnabled(false);
        setStatus("Jarvis düşünüyor…");
        View focused = getCurrentFocus();
        if (focused != null) {
            ((InputMethodManager) getSystemService(Context.INPUT_METHOD_SERVICE))
                    .hideSoftInputFromWindow(focused.getWindowToken(), 0);
        }
        network.execute(() -> {
            try {
                JSONObject response = post("/ask", text, base, token);
                String reply = response.optString("reply", response.optString("error", "Yanıt boş."));
                runOnUiThread(() -> {
                    append("JARVIS", reply);
                    setStatus("Hazır");
                });
            } catch (Exception e) {
                runOnUiThread(() -> setStatus(errorText(e)));
            } finally {
                runOnUiThread(() -> sendButton.setEnabled(true));
            }
        });
    }

    private JSONObject post(String path, String text, String base, String token) throws Exception {
        base = base.replaceAll("/+$", "");
        if (!(base.startsWith("http://") || base.startsWith("https://"))) {
            throw new IllegalArgumentException("Adres http:// veya https:// ile başlamalı.");
        }
        if (token.length() < 32) throw new IllegalArgumentException("Bağlantı kodu eksik veya geçersiz.");

        JSONObject payload = new JSONObject();
        payload.put("token", token);
        if (text != null) payload.put("text", text);
        HttpURLConnection connection = (HttpURLConnection) new URL(base + path).openConnection();
        connection.setRequestMethod("POST");
        connection.setConnectTimeout(8000);
        connection.setReadTimeout(120000);
        connection.setDoOutput(true);
        connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
        byte[] body = payload.toString().getBytes(StandardCharsets.UTF_8);
        try (OutputStream output = connection.getOutputStream()) {
            output.write(body);
        }
        int code = connection.getResponseCode();
        InputStream stream = code >= 400 ? connection.getErrorStream() : connection.getInputStream();
        StringBuilder response = new StringBuilder();
        if (stream != null) {
            try (BufferedReader reader = new BufferedReader(new InputStreamReader(stream, StandardCharsets.UTF_8))) {
                String line;
                while ((line = reader.readLine()) != null) response.append(line);
            }
        }
        connection.disconnect();
        JSONObject json = new JSONObject(response.toString());
        if (code >= 400) throw new IllegalStateException(json.optString("error", "Sunucu HTTP " + code));
        return json;
    }

    private void persistConnection() {
        getSharedPreferences(PREFS, MODE_PRIVATE).edit()
                .putString("address", address.getText().toString().trim())
                .putString("token", accessCode.getText().toString().trim())
                .apply();
    }

    private void append(String who, String text) {
        if (transcript.length() > 50000) transcript.setText("");
        if (transcript.length() > 0) transcript.append("\n\n");
        transcript.append(who + ":\n" + text);
        transcript.post(() -> ((ScrollView) transcript.getParent()).fullScroll(View.FOCUS_DOWN));
    }

    private void setStatus(String text) {
        status.setText(text);
    }

    private String errorText(Exception e) {
        if (e instanceof IllegalArgumentException || e instanceof IllegalStateException) return e.getMessage();
        return "Bağlantı kurulamadı. Bilgisayar açık, aynı Wi-Fi'da ve kod doğru mu kontrol et. ("
                + e.getClass().getSimpleName() + ")";
    }

    @Override
    protected void onDestroy() {
        network.shutdownNow();
        super.onDestroy();
    }
}
