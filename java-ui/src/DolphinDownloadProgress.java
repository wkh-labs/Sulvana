import java.nio.file.Files;
import java.nio.file.Path;
import java.time.Duration;

import javafx.animation.KeyFrame;
import javafx.animation.Timeline;
import javafx.animation.Animation;
import javafx.application.Application;
import javafx.geometry.Insets;
import javafx.geometry.Pos;
import javafx.scene.Scene;
import javafx.scene.control.Label;
import javafx.scene.control.ProgressBar;
import javafx.scene.layout.VBox;
import javafx.stage.Stage;

public final class DolphinDownloadProgress extends Application {
    private static final Path MODEL = Path.of("/home/tanchjim/Documents/Codex/ai-workspace/models/Dolphin3.0-Llama3.1-8B/Dolphin3.0-Llama3.1-8B-Q4_K_M.gguf");
    private static final long TOTAL_BYTES = 4_920_749_472L;
    private long previousBytes;
    private long previousMillis = System.currentTimeMillis();
    private double speed;
    private Timeline refreshTimer;
    private final ProgressBar bar = new ProgressBar(0);
    private final Label percent = new Label();
    private final Label detail = new Label();

    private static String size(double bytes) {
        return String.format("%.2f GB", bytes / 1024 / 1024 / 1024);
    }

    @Override public void start(Stage stage) {
        Label title = new Label("Preparing Sulvana"); title.getStyleClass().add("title");
        Label subtitle = new Label("Dolphin 3.0 · Llama 3.1 8B"); subtitle.getStyleClass().add("subtitle");
        bar.setMaxWidth(Double.MAX_VALUE); bar.getStyleClass().add("download-bar");
        percent.getStyleClass().add("percent"); detail.getStyleClass().add("detail");
        VBox root = new VBox(8, title, subtitle, bar, percent, detail);
        root.setAlignment(Pos.CENTER_LEFT); root.setPadding(new Insets(25)); root.getStyleClass().add("root");
        Scene scene = new Scene(root, 520, 220);
        scene.getStylesheets().add("data:text/css," + " .root { -fx-background-color: #1a1d28; } .title { -fx-font-size: 19px; -fx-font-weight: bold; -fx-text-fill: #f1f2f8; } .subtitle { -fx-font-size: 12px; -fx-text-fill: #aeb5cc; -fx-padding: 0 0 16 0; } .percent { -fx-font-size: 15px; -fx-font-weight: bold; -fx-text-fill: #a78bfa; -fx-padding: 10 0 0 0; } .detail { -fx-font-size: 11px; -fx-text-fill: #c9cedd; } .download-bar > .bar { -fx-background-color: #8066ff; } .download-bar > .track { -fx-background-color: #303647; }");
        stage.setTitle("Sulvana — Downloading Dolphin 8B"); stage.setScene(scene); stage.setResizable(false); stage.show();
        refreshTimer = new Timeline(new KeyFrame(javafx.util.Duration.millis(250), event -> refresh()));
        refreshTimer.setCycleCount(Animation.INDEFINITE);
        refreshTimer.play();
        refresh();
    }

    private void refresh() {
        long bytes;
        try { bytes = Files.exists(MODEL) ? Files.size(MODEL) : 0; } catch (Exception ignored) { bytes = 0; }
        double ratio = Math.min((double) bytes / TOTAL_BYTES, 1.0); bar.setProgress(ratio); percent.setText(String.format("%.1f%% downloaded", ratio * 100));
        long now = System.currentTimeMillis(); long elapsed = now - previousMillis;
        if (elapsed >= 200) { double instant = Math.max(0, bytes - previousBytes) * 1000.0 / elapsed; speed = speed == 0 ? instant : speed * .72 + instant * .28; previousBytes = bytes; previousMillis = now; }
        if (bytes >= TOTAL_BYTES) { detail.setText("Download complete — you can open Sulvana now."); detail.setStyle("-fx-text-fill: #74d8ad;"); return; }
        String extra = "waiting for download data…";
        if (speed > 50_000) { double seconds = (TOTAL_BYTES - bytes) / speed; extra = String.format("%.1f MB/s • about %.0f min left", speed / 1024 / 1024, seconds / 60); }
        detail.setText(size(bytes) + " of " + size(TOTAL_BYTES) + " • " + extra);
    }
}
