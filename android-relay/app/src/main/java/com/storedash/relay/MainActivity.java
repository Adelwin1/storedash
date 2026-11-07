package com.storedash.relay;

import android.Manifest;
import android.app.Activity;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.text.InputType;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

public final class MainActivity
    extends Activity {

    private static final int SMS_PERMISSION_REQUEST =
        1001;

    private EditText backendUrl;
    private EditText relayKey;
    private EditText allowedSenders;
    private TextView status;

    @Override
    protected void onCreate(
        Bundle savedInstanceState
    ) {
        super.onCreate(
            savedInstanceState
        );

        ScrollView scroll =
            new ScrollView(this);

        LinearLayout layout =
            new LinearLayout(this);

        layout.setOrientation(
            LinearLayout.VERTICAL
        );

        int padding =
            dp(20);

        layout.setPadding(
            padding,
            padding,
            padding,
            padding
        );

        TextView title =
            new TextView(this);

        title.setText(
            "StoreDash Relay"
        );

        title.setTextSize(
            26
        );

        layout.addView(
            title,
            matchWrap()
        );

        TextView description =
            new TextView(this);

        description.setText(
            "\nDedicated payment-phone relay.\n"
            + "Only approved payment SMS senders "
            + "are forwarded to StoreDash.\n"
        );

        layout.addView(
            description,
            matchWrap()
        );

        backendUrl =
            field(
                "Backend URL, e.g. https://api.storedash.com"
            );

        backendUrl.setText(
            RelayConfig.backendUrl(
                this
            )
        );

        layout.addView(
            backendUrl,
            matchWrap()
        );

        relayKey =
            field(
                "Relay secret"
            );

        relayKey.setInputType(
            InputType.TYPE_CLASS_TEXT
            | InputType.TYPE_TEXT_VARIATION_PASSWORD
        );

        relayKey.setText(
            RelayConfig.relayKey(
                this
            )
        );

        layout.addView(
            relayKey,
            matchWrap()
        );

        allowedSenders =
            field(
                "Approved SMS senders, comma-separated"
            );

        allowedSenders.setText(
            RelayConfig.allowedSenders(
                this
            )
        );

        layout.addView(
            allowedSenders,
            matchWrap()
        );

        Button save =
            new Button(this);

        save.setText(
            "Save Relay Configuration"
        );

        save.setOnClickListener(
            view -> saveConfiguration()
        );

        layout.addView(
            save,
            matchWrap()
        );

        Button permission =
            new Button(this);

        permission.setText(
            "Grant SMS Permission"
        );

        permission.setOnClickListener(
            view -> requestSmsPermission()
        );

        layout.addView(
            permission,
            matchWrap()
        );

        status =
            new TextView(this);

        status.setTextSize(
            15
        );

        layout.addView(
            status,
            matchWrap()
        );

        scroll.addView(
            layout
        );

        setContentView(
            scroll
        );

        RelayConfig.deviceId(
            this
        );

        refreshStatus();
    }

    @Override
    protected void onResume() {
        super.onResume();

        if (
            status != null
        ) {
            refreshStatus();
        }
    }

    private void saveConfiguration() {
        String url =
            backendUrl
                .getText()
                .toString()
                .trim();

        String key =
            relayKey
                .getText()
                .toString()
                .trim();

        String senders =
            allowedSenders
                .getText()
                .toString()
                .trim();

        if (
            !url.startsWith(
                "https://"
            )
        ) {
            toast(
                "Backend URL must use HTTPS."
            );

            return;
        }

        if (
            key.isBlank()
        ) {
            toast(
                "Relay secret is required."
            );

            return;
        }

        if (
            senders.isBlank()
        ) {
            toast(
                "At least one approved SMS sender is required."
            );

            return;
        }

        RelayConfig.save(
            this,
            url,
            key,
            senders
        );

        toast(
            "Relay configuration saved."
        );

        refreshStatus();
    }

    private void requestSmsPermission() {
        if (
            checkSelfPermission(
                Manifest.permission.RECEIVE_SMS
            )
            == PackageManager.PERMISSION_GRANTED
        ) {
            toast(
                "SMS permission is already granted."
            );

            return;
        }

        requestPermissions(
            new String[]{
                Manifest.permission.RECEIVE_SMS
            },
            SMS_PERMISSION_REQUEST
        );
    }

    @Override
    public void onRequestPermissionsResult(
        int requestCode,
        String[] permissions,
        int[] grantResults
    ) {
        super.onRequestPermissionsResult(
            requestCode,
            permissions,
            grantResults
        );

        if (
            requestCode
            == SMS_PERMISSION_REQUEST
        ) {
            refreshStatus();

            if (
                grantResults.length > 0
                && grantResults[0]
                == PackageManager.PERMISSION_GRANTED
            ) {
                toast(
                    "SMS permission granted."
                );
            } else {
                toast(
                    "SMS permission denied or restricted."
                );
            }
        }
    }

    private void refreshStatus() {
        boolean permission =
            checkSelfPermission(
                Manifest.permission.RECEIVE_SMS
            )
            == PackageManager.PERMISSION_GRANTED;

        status.setText(
            "\nDevice ID:\n"
            + RelayConfig.deviceId(this)
            + "\n\nConfigured: "
            + (
                RelayConfig.isConfigured(this)
                ? "YES"
                : "NO"
            )
            + "\nSMS permission: "
            + (
                permission
                ? "GRANTED"
                : "NOT GRANTED"
            )
            + "\n\nLast status:\n"
            + RelayConfig.lastStatus(this)
        );
    }

    private EditText field(
        String hint
    ) {
        EditText field =
            new EditText(this);

        field.setHint(
            hint
        );

        field.setSingleLine(
            false
        );

        field.setPadding(
            0,
            dp(12),
            0,
            dp(12)
        );

        return field;
    }

    private ViewGroup.LayoutParams matchWrap() {
        return new LinearLayout.LayoutParams(
            ViewGroup.LayoutParams.MATCH_PARENT,
            ViewGroup.LayoutParams.WRAP_CONTENT
        );
    }

    private int dp(
        int value
    ) {
        return Math.round(
            value
            * getResources()
                .getDisplayMetrics()
                .density
        );
    }

    private void toast(
        String value
    ) {
        Toast.makeText(
            this,
            value,
            Toast.LENGTH_SHORT
        ).show();
    }
}
