import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;
import java.util.Base64;

import javafx.animation.PauseTransition;
import javafx.application.Application;
import javafx.application.Platform;
import javafx.concurrent.Worker;
import javafx.scene.Scene;
import javafx.scene.control.Alert;
import javafx.scene.control.ButtonType;
import javafx.scene.image.Image;
import javafx.scene.web.WebEngine;
import javafx.scene.web.WebView;
import javafx.stage.FileChooser;
import javafx.stage.Stage;
import javafx.util.Duration;
import netscape.javascript.JSObject;

public final class SulvanaDesktop extends Application {
    private static final String ADDRESS = "http://127.0.0.1:8766/";
    private static final Path ROOT = Path.of("/home/tanchjim/Documents/Codex/ai-workspace");
    private Stage stage;
    private WebEngine engine;
    private final HostBridge bridge = new HostBridge();

    @Override public void start(Stage window) throws IOException {
        stage = window;
        WebView view = new WebView();
        // Match the interface's dark canvas so the window does not flash white while the page loads.
        view.setPageFill(javafx.scene.paint.Color.web("#1C1C1E"));
        engine = view.getEngine();
        Path data = ROOT.resolve(".runtime/sulvana-webview");
        Files.createDirectories(data);
        engine.setUserDataDirectory(data.toFile());
        engine.setOnError(event -> System.err.println("Sulvana WebView: " + event.getMessage()));
        engine.setOnAlert(event -> System.err.println("Sulvana UI: " + event.getData()));
        engine.setConfirmHandler(message -> {
            Alert alert = new Alert(Alert.AlertType.CONFIRMATION, message, ButtonType.CANCEL, ButtonType.OK);
            alert.initOwner(stage);
            return alert.showAndWait().orElse(ButtonType.CANCEL) == ButtonType.OK;
        });
        engine.getLoadWorker().stateProperty().addListener((observable, oldState, newState) -> {
            if (newState == Worker.State.SUCCEEDED) {
                JSObject windowObject = (JSObject) engine.executeScript("window");
                windowObject.setMember("sulvanaHost", bridge);
                PauseTransition inspection = new PauseTransition(Duration.seconds(1));
                inspection.setOnFinished(event -> {
                    Object label = engine.executeScript("document.querySelector('.brand strong') && document.querySelector('.brand strong').textContent");
                    System.out.println("SULVANA_VIEW_READY " + label);
                    Object streams = engine.executeScript("(function(){try{return typeof ReadableStream+','+typeof Response+','+(typeof Response==='function'&&new Response('x').body?typeof new Response('x').body.getReader:'none')}catch(e){return 'error:'+e.message}})()");
                    System.out.println("SULVANA_STREAM_CAPABILITY " + streams);
                });
                inspection.play();
            }
        });
        engine.locationProperty().addListener((observable, oldAddress, newAddress) -> {
            if (newAddress != null && !newAddress.startsWith(ADDRESS)) {
                Platform.runLater(() -> engine.load(ADDRESS));
            }
        });
        Scene scene = new Scene(view, 1180, 780, javafx.scene.paint.Color.web("#1C1C1E"));
        window.setScene(scene);
        window.setTitle("Sulvana");
        window.getIcons().add(new Image(ROOT.resolve("sulvana-icon.png").toUri().toString()));
        window.setMinWidth(780);
        window.setMinHeight(600);
        window.show();
        engine.load(ADDRESS);
    }

    @Override public void stop() {
        // The model server is owned by the desktop session and remains available
        // for a later Sulvana window. Closing the window frees the UI resources.
        engine.load(null);
    }

    public final class HostBridge {
        public String selectImage() {
            FileChooser picker = new FileChooser();
            picker.setTitle("Attach an image to Sulvana");
            picker.getExtensionFilters().add(new FileChooser.ExtensionFilter("Images", "*.png", "*.jpg", "*.jpeg", "*.webp"));
            java.io.File file = picker.showOpenDialog(stage);
            if (file == null) return "";
            try {
                // Report failures so the page can explain them; an empty string means "cancelled".
                if (Files.size(file.toPath()) > 10_000_000) return "{\"error\":\"too_large\"}";
                byte[] bytes = Files.readAllBytes(file.toPath());
                String suffix = file.getName().toLowerCase();
                String mime = suffix.endsWith(".png") ? "image/png" : suffix.endsWith(".webp") ? "image/webp" : "image/jpeg";
                String name64 = Base64.getEncoder().encodeToString(file.getName().getBytes(java.nio.charset.StandardCharsets.UTF_8));
                return "{\"name64\":\"" + name64 + "\",\"data\":\"data:" + mime + ";base64," + Base64.getEncoder().encodeToString(bytes) + "\"}";
            } catch (IOException error) { return "{\"error\":\"unreadable\"}"; }
        }

        /** Returns "saved", "cancelled", "missing" or "failed" so the page can tell a cancel from an error. */
        public String saveImage(String filename) {
            if (filename == null || !filename.matches("[A-Za-z0-9_.-]+\\.png")) return "missing";
            Path source = ROOT.resolve("runs/z-image").resolve(filename);
            if (!Files.isRegularFile(source)) return "missing";
            FileChooser picker = new FileChooser();
            picker.setTitle("Save generated image");
            picker.setInitialFileName(filename);
            java.io.File target = picker.showSaveDialog(stage);
            if (target == null) return "cancelled";
            try { Files.copy(source, target.toPath(), StandardCopyOption.REPLACE_EXISTING); return "saved"; }
            catch (IOException error) { return "failed"; }
        }
    }
}
