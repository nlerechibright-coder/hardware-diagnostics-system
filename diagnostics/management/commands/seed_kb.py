
"""
Management command to seed the DiagnosticRule knowledge base.

Seeds a decision tree (question -> option -> next_node) with 84 nodes
across 14 categories. Each node is searchable via the SearchIndex.

Run: python manage.py seed_kb [--flush]
"""

from django.core.management.base import BaseCommand
from diagnostics.models import DiagnosticRule, RuleOption, SearchIndex


class Command(BaseCommand):
    help = "Seeds the diagnostic knowledge base with 84 decision tree nodes."

    def add_arguments(self, parser):
        parser.add_argument(
            "--flush",
            action="store_true",
            help="Delete all existing rules before seeding.",
        )

    def handle(self, *args, **options):
        if options["flush"]:
            self.stdout.write("Flushing existing data...")
            DiagnosticRule.objects.all().delete()
            SearchIndex.objects.all().delete()
            self.stdout.write("   Done.\n")

        self.stdout.write("Seeding knowledge base...\n")
        total = 0
        total += self._seed_cpu()
        total += self._seed_ram()
        total += self._seed_storage()
        total += self._seed_gpu()
        total += self._seed_psu()
        total += self._seed_motherboard()
        total += self._seed_boot()
        total += self._seed_bios()
        total += self._seed_display()
        total += self._seed_network()
        total += self._seed_peripherals()
        total += self._seed_audio()
        total += self._seed_laptop()
        total += self._seed_general()

        self.stdout.write(self.style.SUCCESS(
            f"\nKnowledge base seeded: {total} nodes\n"
            f"   Categories: CPU, RAM, Storage, GPU, PSU, Motherboard, Boot, "
            f"BIOS, Display, Network, Peripherals, Audio, Laptop, General\n"
        ))

        self.stdout.write("Rebuilding search index...")
        for rule in DiagnosticRule.objects.filter(is_active=True):
            rule.rebuild_search_index()
        term_count = SearchIndex.objects.count()
        self.stdout.write(self.style.SUCCESS(
            f"   Done. {term_count} search terms indexed.\n"
        ))

    def _rule(self, node_id, category, title, node_type, content,
              severity="MEDIUM", keywords="", related="", reasoning="", recommendation=""):
        rule, created = DiagnosticRule.objects.update_or_create(
            node_id=node_id,
            defaults={
                "category": category, "title": title, "node_type": node_type,
                "content": content, "severity": severity, "search_keywords": keywords,
                "related_rules": related, "reasoning": reasoning,
                "recommendation": recommendation, "is_active": True,
            }
        )
        return rule, created

    def _opt(self, rule, text, next_node=None, order=0):
        RuleOption.objects.filter(rule=rule, option_text=text).delete()
        return RuleOption.objects.create(
            rule=rule, option_text=text, next_node=next_node, order=order
        )

    # =================================================================
    #  CPU (5 nodes)
    # =================================================================

    def _seed_cpu(self):
        self.stdout.write("  CPU...")
        cpu_q, _ = self._rule(
            "CPU-Q1", "CPU", "CPU Issue Detection", "question",
            "Is your computer experiencing performance issues related to the CPU?",
            keywords="cpu, processor, slow, performance, intel, amd"
        )
        cpu_overheat, _ = self._rule(
            "CPU-001", "CPU", "CPU Overheating", "solution",
            """CPU Overheating Detected
            Your CPU temperature exceeds safe operating limits (>85C under load).
            1. Check CPU temperature: Use HWiNFO64, Core Temp, or MSI Afterburner.
            2. Clean dust from heatsink and fans: Use compressed air. Focus on CPU cooler fins.
            3. Reapply thermal paste: Remove old dried paste with isopropyl alcohol, apply pea-sized dot of new paste.
            4. Verify cooler mounting: Ensure heatsink is firmly seated with even pressure.
            5. Improve case airflow: Add intake/exhaust fans. Maintain positive pressure.
            6. Check for overclocking: Reset BIOS to defaults if CPU is overclocked.
            7. Replace cooler: Stock coolers may be inadequate. Consider aftermarket air or AIO liquid cooler.
            Critical: Sustained temps above 95C can cause permanent CPU damage.""",
            severity="HIGH",
            keywords="cpu overheating, high temperature, cpu hot, thermal throttling, cpu fan loud, processor heat",
            reasoning="High CPU temps cause thermal throttling, system instability, and long-term silicon degradation.",
            recommendation="Immediate action required: clean, re-paste, and verify cooling."
        )
        cpu_high, _ = self._rule(
            "CPU-002", "CPU", "High CPU Usage", "solution",
            """High CPU Usage
            CPU usage is consistently above 80% even at idle.
            1. Open Task Manager: Ctrl+Shift+Esc -> Processes -> Sort by CPU.
            2. Identify the culprit: Note which process is consuming CPU.
            3. Common fixes by process:
               - System Idle Process at 90%+ -> This is NORMAL. CPU is resting.
               - Antivirus scanning -> Let it finish or schedule for off-hours.
               - Windows Update (TiWorker, WaasMedic) -> Let it complete.
               - Browser with many tabs -> Close unused tabs.
               - Background apps -> Settings -> Apps -> Startup -> Disable non-essential.
            4. Run malware scan: Crypto-miners and trojans max out CPU silently.
            5. Check for Windows corruption: sfc /scannow and DISM /Online /Cleanup-Image /RestoreHealth
            6. Update drivers: Outdated chipset/GPU drivers can cause DPC latency spikes.""",
            severity="MEDIUM",
            keywords="high cpu usage, cpu 100%, system idle process, cpu spike, task manager cpu, svchost high cpu"
        )
        cpu_missing, _ = self._rule(
            "CPU-003", "CPU", "CPU Not Detected", "solution",
            """CPU Not Detected by BIOS
            System powers on but BIOS shows no CPU or fails to POST.
            1. Check power connections: Ensure 8-pin (4+4) CPU power is connected to motherboard.
            2. Reseat CPU: Power off, remove cooler, lift retention arm, remove and reseat CPU. Check for bent pins (Intel) or damaged pads (AMD).
            3. Clear CMOS: Remove CMOS battery for 5 minutes or use jumper.
            4. Test with minimal hardware: Single RAM stick, no GPU (use integrated), no storage.
            5. Check for bent motherboard pins: LGA socket pins are fragile. Use flashlight and magnifying glass.
            6. Try different motherboard: If CPU works in another board, your motherboard socket is damaged.
            7. Physical damage: If you see burn marks or smell burnt electronics, the CPU or VRM may be fried.""",
            severity="CRITICAL",
            keywords="cpu not detected, no cpu, post fail, blank screen, no beep, cpu fan spins no display"
        )
        cpu_fan, _ = self._rule(
            "CPU-004", "CPU", "CPU Fan Error", "solution",
            """CPU Fan Error
            BIOS reports "CPU Fan Error" on boot.
            1. Check fan connection: Ensure 4-pin CPU_FAN header is used (not SYS_FAN or CHA_FAN).
            2. Verify fan spins: Look inside case during boot. If fan doesn't spin, it's dead.
            3. Check BIOS fan settings: Some BIOSes have minimum RPM thresholds. Lower or disable the warning.
            4. Replace fan: If bearing is seized or blades don't move freely, replace cooler.
            5. AIO pump check: If using liquid cooler, ensure pump is connected to AIO_PUMP or CPU_OPT header.
            6. Temporary workaround: Set "CPU Fan Speed Low Limit" to 200 RPM or "Ignore" in BIOS.
            Do not ignore: Running without CPU cooling will cause thermal shutdown within seconds.""",
            severity="HIGH",
            keywords="cpu fan error, fan not spinning, cpu fan stopped, bios fan error, cooling fan failure"
        )
        cpu_bottleneck, _ = self._rule(
            "CPU-005", "CPU", "CPU Bottleneck", "solution",
            """CPU Bottleneck
            GPU is underutilized while CPU is maxed out -- games/apps stutter.
            1. Confirm bottleneck: Use MSI Afterburner overlay. If GPU usage <80% and CPU = 95-100%, it's a bottleneck.
            2. Lower resolution/settings: Higher resolutions shift load to GPU, reducing CPU bottleneck.
            3. Close background apps: Discord, Chrome, and streaming software consume CPU cycles.
            4. Enable XMP/DOCP: Faster RAM reduces CPU latency. Check BIOS for memory profile.
            5. Overclock CPU: If motherboard supports it, a modest OC can help.
            6. Upgrade CPU: If paired with a high-end GPU (RTX 4070+), an older 4-core CPU will bottleneck. Consider 6-core+ modern CPU.
            7. Check for thermal throttling: A throttling CPU performs worse than it should. See CPU-001.""",
            severity="LOW",
            keywords="cpu bottleneck, stuttering, low fps, gpu not fully used, cpu maxed out, gaming stutter"
        )
        self._opt(cpu_q, "CPU is overheating / running very hot", cpu_overheat, 0)
        self._opt(cpu_q, "CPU usage is constantly high", cpu_high, 1)
        self._opt(cpu_q, "System won't POST / CPU not detected", cpu_missing, 2)
        self._opt(cpu_q, "BIOS shows CPU fan error", cpu_fan, 3)
        self._opt(cpu_q, "Games stutter / GPU underutilized", cpu_bottleneck, 4)
        self.stdout.write("   5 nodes")
        return 5

    # =================================================================
    #  RAM (5 nodes)
    # =================================================================

    def _seed_ram(self):
        self.stdout.write("  RAM...")
        ram_q, _ = self._rule(
            "RAM-Q1", "RAM", "RAM Issue Detection", "question",
            "Are you experiencing memory-related issues?",
            keywords="ram, memory, ddr, stick, dimm"
        )
        ram_insufficient, _ = self._rule(
            "RAM-001", "RAM", "Insufficient RAM", "solution",
            """Insufficient RAM
            System runs out of memory, causing slowdowns and crashes.
            1. Check RAM usage: Task Manager -> Performance -> Memory. If consistently >85%, you need more.
            2. Close unnecessary apps: Chrome tabs are RAM killers. Use extensions like OneTab.
            3. Disable startup programs: Task Manager -> Startup -> Disable non-essential.
            4. Check for memory leaks: Some apps leak RAM over time. Restart them periodically.
            5. Add more RAM: Check motherboard manual for max supported RAM and compatible speeds (DDR4/DDR5).
            6. Enable virtual memory: Control Panel -> System -> Advanced -> Performance -> Settings -> Advanced -> Virtual memory. Set to 1.5x physical RAM.
            7. Check 32-bit vs 64-bit: 32-bit Windows can only use ~3.5GB RAM. Upgrade to 64-bit OS.""",
            severity="MEDIUM",
            keywords="insufficient ram, out of memory, low memory, ram full, need more ram, memory usage high"
        )
        ram_not_detected, _ = self._rule(
            "RAM-002", "RAM", "RAM Not Detected", "solution",
            """RAM Not Detected
            BIOS or Windows shows less RAM than installed.
            1. Reseat RAM modules: Power off, open clips, remove sticks, reinsert until both clips click.
            2. Test one stick at a time: Identify if a specific stick or slot is faulty.
            3. Check slot order: Consult motherboard manual for correct population order (usually A2/B2 first).
            4. Clean contacts: Use pencil eraser on gold contacts, then reseat.
            5. Check BIOS settings: Ensure XMP/DOCP is not overclocking beyond stability.
            6. Update BIOS: Some boards need BIOS updates for larger RAM support.
            7. Check for bent pins: CPU socket pins control memory channels. Bent pins = missing RAM.""",
            severity="HIGH",
            keywords="ram not detected, memory not recognized, less ram than installed, bios shows wrong ram, dimm not working"
        )
        ram_faulty, _ = self._rule(
            "RAM-003", "RAM", "Faulty RAM / Memory Errors", "solution",
            """Faulty RAM / Memory Errors
            Random crashes, BSODs with memory-related codes, or data corruption.
            1. Run Windows Memory Diagnostic: Search in Start menu -> Restart now and check.
            2. Run MemTest86: Create bootable USB, run 4+ passes. Any red errors = bad RAM.
            3. Test sticks individually: Remove all but one, test each slot. Isolate faulty stick.
            4. Check for overheating: RAM doesn't normally overheat, but poor case airflow can affect stability.
            5. Reduce RAM speed: If XMP causes errors, disable it and run at JEDEC standard speed.
            6. Replace faulty stick: RAM has lifetime warranty from most manufacturers.
            Common BSOD codes: MEMORY_MANAGEMENT, IRQL_NOT_LESS_OR_EQUAL, PAGE_FAULT_IN_NONPAGED_AREA""",
            severity="HIGH",
            keywords="faulty ram, memory error, ram crash, bsod memory, memtest86, memory corruption, bad ram stick"
        )
        ram_speed, _ = self._rule(
            "RAM-004", "RAM", "RAM Running at Wrong Speed", "solution",
            """RAM Running Below Rated Speed
            You bought 3200MHz RAM but it runs at 2133MHz or 2400MHz.
            1. Enable XMP (Intel) / DOCP (AMD): BIOS -> AI Tweaker/OC -> Enable XMP Profile 1.
            2. Check BIOS shows correct speed: Main BIOS page should show target frequency.
            3. Verify in Windows: Task Manager -> Performance -> Memory -> Speed. Should match XMP.
            4. If XMP unstable: Try XMP Profile 2 (lower speed), or manually set frequency and timings.
            5. Update BIOS: Newer AGESA (AMD) or Intel microcode improves memory compatibility.
            6. Check QVL: Motherboard Qualified Vendor List -- your RAM kit may not be validated for that board.
            Note: Running RAM below rated speed wastes money but doesn't cause instability.""",
            severity="LOW",
            keywords="ram speed wrong, xmp not working, ram slow, memory frequency low, ddr4 2133 instead of 3200"
        )
        ram_upgrade, _ = self._rule(
            "RAM-005", "RAM", "RAM Upgrade Compatibility", "solution",
            """RAM Upgrade Guide
            Planning to add or replace RAM sticks.
            1. Check current RAM: CPU-Z -> SPD tab -> Note brand, model, speed, timings, voltage.
            2. Match specs: New RAM should match: DDR generation (4/5), speed (MHz), voltage (1.2V/1.35V).
            3. Capacity per slot: Check motherboard manual for max per slot and total max.
            4. Dual channel: For best performance, use 2 or 4 sticks in matched pairs.
            5. Mixed brands: Can work but not guaranteed. Same model/speed/timings = safest.
            6. Install in correct slots: Usually A2 and B2 (2nd and 4th slots from CPU). Check manual.
            7. Test after install: Run MemTest86 to verify stability before trusting the system.""",
            severity="LOW",
            keywords="ram upgrade, add ram, memory upgrade, ddr4 vs ddr5, compatible ram, how much ram do i need"
        )
        self._opt(ram_q, "System is slow / running out of memory", ram_insufficient, 0)
        self._opt(ram_q, "BIOS shows less RAM than installed", ram_not_detected, 1)
        self._opt(ram_q, "Random crashes / BSODs", ram_faulty, 2)
        self._opt(ram_q, "RAM speed is lower than advertised", ram_speed, 3)
        self._opt(ram_q, "I want to upgrade my RAM", ram_upgrade, 4)
        self.stdout.write("   5 nodes")
        return 5

    # =================================================================
    #  Storage (5 nodes)
    # =================================================================

    def _seed_storage(self):
        self.stdout.write("  Storage...")
        sto_q, _ = self._rule(
            "STO-Q1", "Storage", "Storage Issue Detection", "question",
            "Are you having problems with hard drives or SSDs?",
            keywords="hdd, ssd, storage, disk, drive, nvme, sata"
        )
        sto_not_detected, _ = self._rule(
            "STO-001", "Storage", "Drive Not Detected", "solution",
            """Drive Not Detected
            BIOS or Windows doesn't see the hard drive or SSD.
            1. Check physical connections: SATA data cable and power cable firmly seated. Try different SATA port.
            2. Check BIOS: Ensure SATA mode is AHCI (not RAID or IDE unless you need RAID).
            3. Check Disk Management: diskmgmt.msc -- drive may need initialization or letter assignment.
            4. Listen for sounds: Clicking = physical failure. No spin = power or PCB issue.
            5. Test on another PC: If drive isn't detected anywhere, it's likely dead.
            6. For NVMe: Ensure M.2 slot supports your drive size (2280, 2260) and protocol (SATA vs NVMe).
            7. Update chipset drivers: AMD/SATA/NVMe controller drivers from motherboard manufacturer.
            If clicking: Stop immediately. This indicates head crash. Seek professional data recovery.""",
            severity="HIGH",
            keywords="drive not detected, hdd not showing, ssd missing, disk not found, bios no drive, nvme not detected"
        )
        sto_failing, _ = self._rule(
            "STO-002", "Storage", "Drive Failing / SMART Errors", "solution",
            """Drive Failing / SMART Errors
            SMART warnings, bad sectors, or sudden performance degradation.
            1. Check SMART status: CrystalDiskInfo (free) -> Health Status. Yellow = caution, Red = failing.
            2. Key SMART attributes to watch:
               - Reallocated Sectors Count >0 = bad sectors remapped
               - Current Pending Sector Count >0 = unstable sectors
               - Uncorrectable Error Count >0 = unrecoverable read errors
               - Wear Leveling Count (SSD) -- lower % = more worn
            3. Back up data IMMEDIATELY: A failing drive can die without warning.
            4. Run chkdsk /f /r: Attempts to fix file system errors and recover bad sectors.
            5. Check cables: Intermittent connection can mimic drive failure symptoms.
            6. Replace the drive: Once SMART shows caution, failure is imminent. Days to weeks.
            SSD note: SSDs don't click but can fail silently. Watch for sudden read-only mode or disappearance from BIOS.""",
            severity="CRITICAL",
            keywords="smart error, drive failing, bad sectors, hdd clicking, ssd dying, crystal disk info, reallocated sectors"
        )
        sto_full, _ = self._rule(
            "STO-003", "Storage", "Disk Full / Low Space", "solution",
            """Disk Full / Low Space
            Running out of storage space, causing performance issues.
            1. Check what's using space: Settings -> System -> Storage -> See what's consuming space.
            2. Run Disk Cleanup: cleanmgr -> Clean system files -> Remove Windows Update cache, temp files, Recycle Bin.
            3. Move large folders: Documents, Downloads, Videos to external drive or cloud.
            4. Uninstall unused programs: Control Panel -> Programs -> Sort by size.
            5. Use TreeSize or WinDirStat: Visualize what's eating space. Often it's hiberfil.sys, pagefile.sys, or old backups.
            6. Disable hibernation: powercfg /hibernate off (saves RAM-size GBs).
            7. Move pagefile: Advanced System Settings -> Performance -> Advanced -> Virtual memory -> Move to secondary drive.
            8. Upgrade storage: Add larger HDD/SSD or replace existing drive.""",
            severity="MEDIUM",
            keywords="disk full, low space, storage full, c drive full, out of disk space, clean up disk"
        )
        sto_slow, _ = self._rule(
            "STO-004", "Storage", "Slow Drive Performance", "solution",
            """Slow Drive Performance
            HDD/SSD is much slower than expected.
            1. Check drive health: CrystalDiskInfo for SMART, CrystalDiskMark for speed test.
            2. For HDDs:
               - Defragment: Only for HDDs. Search "Defragment" in Start menu.
               - Check for fragmentation >10%.
               - Ensure drive isn't nearly full. HDDs slow down when >90% full.
            3. For SSDs:
               - NEVER defrag SSDs. It wears them out and provides no benefit.
               - Ensure TRIM is enabled: fsutil behavior query DisableDeleteNotify. 0 = enabled.
               - Check SATA mode: Must be AHCI. IDE mode cripples SSD performance.
               - Check cable: Use SATA 6Gb/s cable and port. Older cables limit speed.
            4. Background processes: Check Task Manager for high disk usage processes.
            5. Malware scan: Some malware causes constant disk thrashing.
            6. Update firmware: SSD manufacturers release firmware updates for performance fixes.""",
            severity="MEDIUM",
            keywords="slow hdd, slow ssd, disk slow, low read speed, low write speed, ssd not fast, hdd fragmentation"
        )
        sto_data_recovery, _ = self._rule(
            "STO-005", "Storage", "Data Recovery", "solution",
            """Data Recovery
            Files were deleted or drive is failing and you need data back.
            1. Stop using the drive immediately: Every write operation risks overwriting deleted data.
            2. Check Recycle Bin: Obvious but often overlooked.
            3. Use recovery software:
               - Recuva (free, good for simple cases)
               - TestDisk (free, powerful, command-line)
               - R-Studio (paid, professional grade)
            4. For formatted drives: Don't write anything new. Use deep scan recovery tools.
            5. For physically damaged drives: If drive clicks, beeps, or isn't detected -- STOP. Send to professional data recovery service.
            6. Prevent future loss: Set up regular backups. Windows File History, Mac Time Machine, or cloud sync (OneDrive, Google Drive).
            7. RAID arrays: Don't attempt DIY recovery. Contact specialist immediately.""",
            severity="HIGH",
            keywords="data recovery, deleted files, recover data, formatted drive, file recovery, lost files, undelete"
        )
        self._opt(sto_q, "Drive not showing up in BIOS or Windows", sto_not_detected, 0)
        self._opt(sto_q, "SMART warnings or bad sectors", sto_failing, 1)
        self._opt(sto_q, "Running out of disk space", sto_full, 2)
        self._opt(sto_q, "Drive is very slow", sto_slow, 3)
        self._opt(sto_q, "I need to recover deleted/lost data", sto_data_recovery, 4)
        self.stdout.write("   5 nodes")
        return 5

    # =================================================================
    #  GPU (5 nodes)
    # =================================================================

    def _seed_gpu(self):
        self.stdout.write("  GPU...")
        gpu_q, _ = self._rule(
            "GPU-Q1", "GPU", "GPU Issue Detection", "question",
            "Are you experiencing graphics or display-related problems?",
            keywords="gpu, graphics card, video card, nvidia, amd, rtx, display"
        )
        gpu_artifact, _ = self._rule(
            "GPU-001", "GPU", "GPU Artifacts / Visual Glitches", "solution",
            """GPU Artifacts / Visual Glitches
            Strange colors, lines, or shapes on screen, especially during 3D rendering.
            1. Check temperatures: GPU overheating causes artifacts. Use MSI Afterburner or GPU-Z.
            2. Clean GPU: Remove dust from heatsink and fans. Check thermal paste on GPU die (advanced).
            3. Underclock GPU: Reduce core clock by 50-100MHz in MSI Afterburner to test stability.
            4. Update drivers: DDU (Display Driver Uninstaller) in Safe Mode, then install latest drivers.
            5. Test in another PC: If artifacts follow the GPU, the card is failing.
            6. Check VRAM: Artifacts often indicate failing VRAM. This is usually unrepairable.
            7. Reduce power limit: Lower power to 80% to reduce strain on failing components.
            8. Warranty/RMA: If under warranty, RMA immediately. Don't attempt self-repair on new cards.""",
            severity="HIGH",
            keywords="gpu artifacts, screen glitches, visual artifacts, colored lines, gpu corruption, screen tearing, weird colors"
        )
        gpu_crash, _ = self._rule(
            "GPU-002", "GPU", "GPU Driver Crashes / Black Screen", "solution",
            """GPU Driver Crashes / Black Screen
            Screen goes black, driver crashes (TDR), or system freezes during GPU load.
            1. Check Event Viewer: Windows Logs -> System -> Look for "Display driver nvlddmkm stopped responding".
            2. DDU clean install: Boot to Safe Mode, run Display Driver Uninstaller, reinstall latest stable driver (not beta).
            3. Check power supply: GPU power cables must be fully seated. Use separate PCIe cables, not daisy-chained for high-end cards.
            4. Check temperatures: Overheating GPU triggers protective shutdowns.
            5. Disable overclock: Reset GPU to stock clocks. Unstable OCs cause TDRs.
            6. Increase TDR delay: Registry edit TdrDelay to 10 seconds (advanced).
            7. Test with different GPU: If crashes stop, your GPU is likely failing.
            8. BIOS update: Some motherboards need updates for new GPU compatibility (especially PCIe 4.0/5.0).""",
            severity="HIGH",
            keywords="gpu crash, black screen, driver stopped responding, tdr failure, nvlddmkm, display driver crash"
        )
        gpu_no_output, _ = self._rule(
            "GPU-003", "GPU", "GPU No Output / Not Detected", "solution",
            """GPU No Output / Not Detected
            Monitor shows no signal or BIOS doesn't list the graphics card.
            1. Check monitor connection: Ensure cable is plugged into GPU, not motherboard (common mistake).
            2. Reseat GPU: Power off, remove card, check PCIe slot for debris, reinsert firmly until latch clicks.
            3. Check power cables: 6-pin, 8-pin, or 12VHPWR must be fully connected. Listen for click.
            4. Test different slot: Try lower PCIe x16 slot. Some boards disable upper slot if M.2 is populated.
            5. Test with integrated graphics: Remove GPU, use motherboard video output to verify system POSTs.
            6. Check BIOS settings: Ensure primary display is set to PCIe, not iGPU.
            7. Test GPU in another system: If it works elsewhere, your motherboard PCIe slot may be damaged.
            8. For new builds: Some high-end GPUs need BIOS update for Resizable BAR / above 4G decoding.""",
            severity="CRITICAL",
            keywords="gpu not detected, no signal, monitor no display, gpu not working, black screen gpu, no video output"
        )
        gpu_perf, _ = self._rule(
            "GPU-004", "GPU", "Low GPU Performance", "solution",
            """Low GPU Performance
            Games run slower than expected for your GPU model.
            1. Check GPU usage: MSI Afterburner overlay. If GPU <50% at 1080p, likely CPU bottleneck.
            2. Check power mode: Windows -> Power Options -> High Performance. NVIDIA Control Panel -> Manage 3D -> Power Management -> Prefer Maximum Performance.
            3. Check resolution and settings: 4K is 4x the pixels of 1080p. Lower settings if needed.
            4. Check temperatures: Thermal throttling above 83C (NVIDIA) or 90C (AMD reference).
            5. PCIe lane width: GPU-Z -> Bus Interface. Should be x16. x8 or x4 = motherboard/slot issue.
            6. Background apps: Close recording software, browsers, and streaming apps.
            7. Driver version: Sometimes latest drivers regress performance. Try previous stable version.
            8. Resizable BAR: Enable in BIOS for 5-10% performance boost on supported cards.""",
            severity="LOW",
            keywords="low gpu performance, low fps, gpu underperforming, weak gpu, games slow, bad benchmark scores"
        )
        gpu_upgrade, _ = self._rule(
            "GPU-005", "GPU", "GPU Upgrade Guide", "solution",
            """GPU Upgrade Guide
            Choosing and installing a new graphics card.
            1. Check PSU wattage: Add 100W headroom to GPU TDP. RTX 4070 needs ~650W PSU minimum.
            2. Check physical space: Measure case clearance. High-end cards are 3+ slots wide and 300mm+ long.
            3. Check PCIe power: Ensure PSU has correct cables (6-pin, 8-pin, 12VHPWR for RTX 40-series).
            4. CPU bottleneck: Pairing RTX 4090 with i5-8400 wastes money. Match GPU to CPU tier.
            5. Monitor resolution: 1080p -> RTX 4060/RX 7600. 1440p -> RTX 4070/RX 7800 XT. 4K -> RTX 4080+/RX 7900 XTX.
            6. Installation: Uninstall old drivers with DDU, power off, install card, boot, install new drivers.
            7. BIOS settings: Enable Resizable BAR and Above 4G Decoding for modern cards.
            8. Sell old card: Used GPU market is strong. List on eBay, Facebook Marketplace, or hardware swap forums.""",
            severity="LOW",
            keywords="gpu upgrade, new graphics card, which gpu to buy, rtx vs amd, gpu recommendation, install gpu"
        )
        self._opt(gpu_q, "Screen shows artifacts, lines, or weird colors", gpu_artifact, 0)
        self._opt(gpu_q, "Games crash to desktop or black screen", gpu_crash, 1)
        self._opt(gpu_q, "No display / GPU not detected", gpu_no_output, 2)
        self._opt(gpu_q, "Low FPS / underperforming GPU", gpu_perf, 3)
        self._opt(gpu_q, "I want to upgrade my GPU", gpu_upgrade, 4)
        self.stdout.write("   5 nodes")
        return 5

    # =================================================================
    #  PSU (5 nodes)
    # =================================================================

    def _seed_psu(self):
        self.stdout.write("  PSU...")
        psu_q, _ = self._rule(
            "PSU-Q1", "PSU", "PSU Issue Detection", "question",
            "Is your power supply causing system instability?",
            keywords="psu, power supply, power, wattage, corsair, evga, seasonic"
        )
        psu_random_shutdown, _ = self._rule(
            "PSU-001", "PSU", "Random Shutdowns / Restarts", "solution",
            """Random Shutdowns / Restarts
            System powers off unexpectedly, often under load.
            1. Check event log: Event Viewer -> System -> Look for Kernel-Power 41 (unexpected shutdown).
            2. Check temperatures: CPU/GPU overheating triggers protective shutdown. See CPU-001 and GPU-001.
            3. Stress test PSU: Use OCCT PSU test or Prime95 + FurMark simultaneously. If it shuts down, PSU is suspect.
            4. Check wattage: Calculate total system power draw. PSU should have 20% headroom above peak draw.
            5. Check cables: Ensure 24-pin motherboard and 8-pin CPU are fully seated. Loose cables cause instability.
            6. Test with known-good PSU: Borrow or buy from store with return policy. If stable, replace PSU.
            7. Check wall outlet: Faulty outlet or power strip can cause issues. Try different outlet/circuit.
            8. Age of PSU: Capacitors degrade after 5-7 years. Older PSUs lose capacity and stability.""",
            severity="HIGH",
            keywords="random shutdown, unexpected restart, system powers off, kernel power 41, psu failure, computer turns off"
        )
        psu_noise, _ = self._rule(
            "PSU-002", "PSU", "PSU Noise / Coil Whine", "solution",
            """PSU Noise / Coil Whine
            High-pitched whining, buzzing, or clicking from the power supply.
            1. Identify the source: Use cardboard tube or stethoscope to pinpoint noise. GPU and PSU both coil whine.
            2. Coil whine: Caused by inductors vibrating under load. Not dangerous, just annoying.
            3. Fixes for coil whine:
               - Limit FPS: High FPS (300+ in menus) causes coil whine. Cap to monitor refresh rate.
               - Change power plan: Some PSUs whine less on different voltage regulation modes.
               - Physical dampening: Rubber washers between PSU and case can reduce vibration transfer.
            4. Rattling/grinding: Fan bearing failure. Replace PSU immediately -- fan failure leads to overheating.
            5. Clicking: Relay switching or arcing. Very dangerous. Unplug and replace PSU immediately.
            6. RMA: If under warranty, most manufacturers will replace for excessive noise.""",
            severity="MEDIUM",
            keywords="psu noise, coil whine, buzzing psu, clicking power supply, loud psu, psu fan noise"
        )
        psu_burning, _ = self._rule(
            "PSU-003", "PSU", "Burning Smell / Smoke", "solution",
            """Burning Smell / Smoke from PSU
            SMELLS LIKE BURNING ELECTRONICS OR SEE SMOKE -- EMERGENCY.
            1. UNPLUG IMMEDIATELY: Do not pass go. Pull the power cord from the wall.
            2. Do not attempt to power on: A burning PSU can damage every component connected to it.
            3. Inspect visually: Look for bulging capacitors, burn marks, or melted plastic on PSU exterior.
            4. Check other components: PSU failures often cascade. Test motherboard, GPU, and drives with known-good PSU.
            5. Do not open PSU: Even unplugged, capacitors hold lethal charge. Leave to professionals.
            6. Replace PSU: Never reuse a PSU that smoked or smelled burnt. Risk of fire and component death.
            7. Consider higher quality unit: The PSU is the one component you should never cheap out on. Buy 80+ Gold or better from reputable brand.
            8. Check insurance: If fire damage occurred, document everything for home/renters insurance claim.""",
            severity="CRITICAL",
            keywords="burning smell, smoke, psu fire, burnt electronics, melting plastic, electrical fire, psu exploded"
        )
        psu_wattage, _ = self._rule(
            "PSU-004", "PSU", "Insufficient Wattage", "solution",
            """Insufficient Wattage
            System unstable or won't boot after adding new components.
            1. Calculate power draw: Use OuterVision PSU Calculator or similar. Include CPU, GPU, drives, fans, and 20% headroom.
            2. Check PSU label: Look for continuous wattage, not peak. A "600W" PSU may only deliver 450W continuous.
            3. Symptoms of insufficient PSU:
               - System shuts down during GPU load (gaming, rendering)
               - Won't boot with new GPU installed
               - USB devices disconnect under load
               - Random freezes and crashes
            4. Upgrade PSU: Buy quality unit with 20% more wattage than calculated peak draw.
            5. Efficiency matters: 80+ Bronze vs Platinum affects power draw from wall, not output capacity.
            6. Single vs multi-rail: Single rail is simpler. Multi-rail can trip if one rail is overloaded.
            7. Future-proof: If planning GPU upgrade, buy PSU for the target GPU now.""",
            severity="HIGH",
            keywords="insufficient wattage, psu too weak, not enough power, wattage calculator, psu upgrade, power draw"
        )
        psu_cables, _ = self._rule(
            "PSU-005", "PSU", "Cable / Connector Issues", "solution",
            """Cable / Connector Issues
            Loose, damaged, or incorrect power cables causing instability.
            1. Check all connections: 24-pin motherboard, 8-pin CPU, 6/8-pin PCIe GPU, SATA power.
            2. Listen for clicks: Modular cables should click into place. If not fully seated, arcing occurs.
            3. Don't mix modular cables: PSU modular cables are NOT interchangeable between brands. Wrong cable = fire hazard.
            4. Check for damage: Frayed wires, melted connectors, or discolored pins indicate overheating.
            5. Daisy-chain GPU power: For GPUs >225W, use separate PCIe cables per connector. Don't daisy-chain from one cable.
            6. 12VHPWR adapter: For RTX 40-series, use native 12VHPWR cable or 4x8-pin adapter. 3x8-pin is insufficient for 4090.
            7. Cable management: Don't force cables at extreme angles. Stress on connectors causes intermittent contact.
            8. Replace damaged cables: Contact PSU manufacturer for replacement modular cables. Don't use third-party cables unless verified compatible.""",
            severity="HIGH",
            keywords="psu cable, loose cable, modular cable, 12vhpwr, gpu power cable, cable not seated, wrong cable"
        )
        self._opt(psu_q, "Random shutdowns or restarts", psu_random_shutdown, 0)
        self._opt(psu_q, "PSU makes noise (whine, buzz, click)", psu_noise, 1)
        self._opt(psu_q, "Burning smell or smoke", psu_burning, 2)
        self._opt(psu_q, "New GPU/component won't work / system unstable", psu_wattage, 3)
        self._opt(psu_q, "Cable/connector problems", psu_cables, 4)
        self.stdout.write("   5 nodes")
        return 5

    # =================================================================
    #  Motherboard (5 nodes)
    # =================================================================

    def _seed_motherboard(self):
        self.stdout.write("  Motherboard...")
        mb_q, _ = self._rule(
            "MB-Q1", "Motherboard", "Motherboard Issue Detection", "question",
            "Are you experiencing motherboard-related problems?",
            keywords="motherboard, mobo, mainboard, asus, gigabyte, msi, asrock"
        )
        mb_no_post, _ = self._rule(
            "MB-001", "Motherboard", "No POST / No Power", "solution",
            """No POST / No Power
            System shows no signs of life or fails to complete POST.
            1. Check power: Is PSU switch on? Is power cable firmly connected? Try different outlet.
            2. Check front panel connectors: Power switch, reset switch, and LED pins must be correctly connected to motherboard.
            3. Paperclip test PSU: Short green wire to black wire on 24-pin connector. PSU fan should spin. If not, PSU is dead.
            4. Minimal boot: Remove GPU, all but one RAM stick, all storage. Use integrated graphics if available.
            5. Check for shorts: Ensure motherboard standoffs are correctly placed. Extra standoff behind motherboard = short circuit.
            6. Check CPU power: 8-pin (4+4) CPU power must be connected. System won't POST without it.
            7. Listen for beep codes: Single beep = normal POST. Multiple beeps = specific error (check motherboard manual).
            8. Check Q-LEDs / Dr. Debug: Modern boards have LED indicators for CPU, DRAM, VGA, BOOT. Note which stays lit.
            9. Clear CMOS: Remove battery for 5 minutes or use jumper. Corrupted BIOS settings prevent POST.""",
            severity="CRITICAL",
            keywords="no post, no power, wont turn on, blank screen, no beep, motherboard dead, system wont start"
        )
        mb_usb, _ = self._rule(
            "MB-002", "Motherboard", "USB Ports Not Working", "solution",
            """USB Ports Not Working
            USB devices not recognized or intermittently disconnect.
            1. Check specific ports: Test all ports. If only front panel ports fail, case cable may be loose.
            2. Check Device Manager: Look for yellow triangles on USB controllers. Uninstall and let Windows reinstall.
            3. Update chipset drivers: USB controllers are part of chipset. Download from motherboard manufacturer.
            4. Check BIOS: Ensure USB ports are enabled. Some boards have options to disable front/rear USB separately.
            5. Power management: Device Manager -> USB Root Hub -> Properties -> Power Management -> Uncheck "Allow computer to turn off this device".
            6. Check for physical damage: Bent pins in USB 3.0 header can short and disable all front ports.
            7. USB power draw: Some ports share power. Too many high-draw devices can overload the controller.
            8. BIOS update: Some boards have USB compatibility issues fixed in newer BIOS versions.""",
            severity="MEDIUM",
            keywords="usb not working, usb ports dead, usb device not recognized, usb disconnecting, front usb not working"
        )
        mb_cmos, _ = self._rule(
            "MB-003", "Motherboard", "CMOS / BIOS Settings Lost", "solution",
            """CMOS / BIOS Settings Lost
            BIOS resets to defaults every time power is disconnected.
            1. Replace CMOS battery: CR2032 coin cell, ~$2. Most common cause of lost settings.
            2. Check battery voltage: Should be 3V. Below 2.5V = replace immediately.
            3. Check for corrosion: Battery leakage can damage socket and nearby components.
            4. Reconfigure BIOS: After battery replacement, re-enter all custom settings (XMP, boot order, fan curves).
            5. Save profile: Most modern BIOSes allow saving settings to USB. Do this before battery replacement.
            6. Check for short: If battery is good but settings still reset, trace for shorted CMOS clear jumper.
            7. Motherboard damage: If none of above work, RTC circuit on motherboard may be damaged. Professional repair or replacement needed.""",
            severity="MEDIUM",
            keywords="cmos reset, bios settings lost, cmos battery, clock wrong, time reset, bios defaults every boot"
        )
        mb_pcie, _ = self._rule(
            "MB-004", "Motherboard", "PCIe Slot Issues", "solution",
            """PCIe Slot Issues
            GPU or expansion cards not working in specific slots.
            1. Check slot configuration: Some slots share lanes with M.2 or SATA. Consult manual for lane allocation.
            2. Reseat card: Remove and reinsert firmly until latch clicks. Check for debris in slot.
            3. Test in different slot: If upper x16 slot fails, try lower slot. If works, upper slot may be damaged.
            4. Check BIOS settings: Some boards allow setting PCIe speed (Gen3/Gen4/Gen5). Mismatch can cause issues.
            5. Physical damage: Look for bent pins or scorch marks in PCIe slot. Damaged slots are rarely repairable.
            6. Update BIOS: Newer AGESA or Intel microcode improves PCIe stability and compatibility.
            7. Check card in another system: If card works elsewhere, motherboard slot is the problem.
            8. Riser cables: Cheap riser cables can cause signal degradation. Use quality shielded riser for vertical GPU mounts.""",
            severity="HIGH",
            keywords="pcie slot, gpu slot not working, expansion card not detected, pcie lane, m2 conflicts, slot broken"
        )
        mb_led, _ = self._rule(
            "MB-005", "Motherboard", "Motherboard LEDs / Debug Codes", "solution",
            """Motherboard LEDs / Debug Codes
            Understanding diagnostic LEDs and POST codes on modern motherboards.
            1. Q-LEDs (ASUS) / EZ Debug LED (MSI):
               - CPU LED solid = CPU not detected or failed
               - DRAM LED solid = RAM not detected or incompatible
               - VGA LED solid = GPU not detected or failed
               - BOOT LED solid = Boot device not found
            2. Dr. Debug / POST Code display: Two-digit hex code. Check motherboard manual for specific meaning.
            3. Common codes:
               - 00, C0, C1 = CPU initialization failed
               - 55 = Memory not installed or incompatible
               - d6 = No VGA output device
               - A2 = IDE detect (usually stuck on SATA detection)
            4. If LED cycles normally then stops: This is normal POST sequence. Only worry if one stays lit.
            5. If no LEDs light: PSU or motherboard power delivery failure. Check 24-pin and 8-pin CPU.
            6. Flashing patterns: Some boards use flashing to indicate specific states. Check manual.
            7. RGB issues: If only RGB doesn't work, check RGB software and 3-pin/4-pin header connections.""",
            severity="LOW",
            keywords="motherboard led, debug code, q led, ez debug, post code, dr debug, motherboard lights, error code"
        )
        self._opt(mb_q, "System won't POST or power on", mb_no_post, 0)
        self._opt(mb_q, "USB ports not working", mb_usb, 1)
        self._opt(mb_q, "BIOS settings reset every boot", mb_cmos, 2)
        self._opt(mb_q, "GPU/expansion card not detected in slot", mb_pcie, 3)
        self._opt(mb_q, "Motherboard LEDs or debug codes", mb_led, 4)
        self.stdout.write("   5 nodes")
        return 5

    # =================================================================
    #  Boot (5 nodes)
    # =================================================================

    def _seed_boot(self):
        self.stdout.write("  Boot...")
        boot_q, _ = self._rule(
            "BOOT-Q1", "Boot", "Boot Issue Detection", "question",
            "Is your system failing to boot into the operating system?",
            keywords="boot, startup, windows wont start, wont boot, boot failure"
        )
        boot_bcd, _ = self._rule(
            "BOOT-001", "Boot", "Boot Configuration Data (BCD) Corruption", "solution",
            """BCD Corruption
            Windows fails to boot with error about BCD or boot configuration.
            1. Create Windows installation USB: Use Media Creation Tool on another PC.
            2. Boot from USB: Change boot order in BIOS or use boot menu (F12/F11/Esc).
            3. Choose "Repair your computer" -> Troubleshoot -> Command Prompt.
            4. Rebuild BCD:
               bootrec /fixmbr
               bootrec /fixboot
               bootrec /scanos
               bootrec /rebuildbcd
            5. If "Access is denied" on fixboot: Use diskpart to assign drive letter, then retry.
            6. Check disk health: chkdsk C: /f /r (may need to schedule on restart).
            7. System Restore: If BCD repair fails, try restoring to earlier restore point.
            8. Clean install: Last resort. Back up data first if possible (use live Linux USB to copy files).""",
            severity="HIGH",
            keywords="bcd error, boot configuration, windows wont start, bootrec, fixboot, access denied, boot manager missing"
        )
        boot_disk, _ = self._rule(
            "BOOT-002", "Boot", "Boot Device Not Found", "solution",
            """Boot Device Not Found
            BIOS reports no bootable device or "No boot disk detected."
            1. Check BIOS boot order: Ensure OS drive is first in boot priority.
            2. Check SATA/NVMe connections: Loose cables or improperly seated M.2 = no boot device.
            3. Check if drive detected in BIOS: If not listed, see STO-001 (Drive Not Detected).
            4. Check boot mode: UEFI vs Legacy. Windows installed in UEFI won't boot in Legacy mode and vice versa.
            5. Disable Secure Boot temporarily: Sometimes Secure Boot prevents valid bootloaders from loading.
            6. Rebuild BCD: See BOOT-001 for bootrec commands.
            7. Check for drive failure: If BIOS sees drive but won't boot, drive may be failing. See STO-002.
            8. For RAID arrays: RAID configuration may have been lost. Reconfigure in BIOS/RAID utility.""",
            severity="CRITICAL",
            keywords="no boot device, boot device not found, no boot disk, bios no bootable device, startup device missing"
        )
        boot_loop, _ = self._rule(
            "BOOT-003", "Boot", "Boot Loop / Automatic Repair Loop", "solution",
            """Boot Loop / Automatic Repair Loop
            Windows repeatedly tries to repair itself and fails, restarting endlessly.
            1. Boot from Windows USB: See BOOT-001 for USB creation.
            2. Try Safe Mode: Boot from USB -> Repair -> Startup Settings -> Enable Safe Mode.
            3. If Safe Mode works: Recent driver or Windows update is the culprit. Uninstall in Safe Mode.
            4. Disable automatic restart: In Startup Settings, disable automatic restart to see blue screen error code.
            5. System Restore: Restore to point before the problem started.
            6. Uninstall updates: Settings -> Windows Update -> Update history -> Uninstall updates.
            7. Check disk: chkdsk and sfc /scannow from recovery command prompt.
            8. Registry rollback: If you have registry backup, restore from command prompt.
            9. Reset PC: Keep my files or Remove everything. Less destructive than clean install.
            10. Clean install: Last resort. Back up data first.""",
            severity="HIGH",
            keywords="boot loop, automatic repair, preparing automatic repair, windows restart loop, infinite boot, recovery loop"
        )
        boot_slow, _ = self._rule(
            "BOOT-004", "Boot", "Slow Boot Times", "solution",
            """Slow Boot Times
            System takes unusually long to reach desktop.
            1. Check startup programs: Task Manager -> Startup -> Disable non-essential. High impact items first.
            2. Check boot drive health: Slow SSDs or failing HDDs cause long boot. See STO-002.
            3. Fast Startup: Windows -> Power Options -> Choose what power buttons do -> Turn on fast startup.
            4. BIOS settings: Disable full logo screen, enable fast boot in BIOS. Skip memory test if option exists.
            5. Check for malware: Some malware significantly slows boot. Run full scan.
            6. Update drivers: Outdated chipset or storage drivers can cause boot delays.
            7. Disable unnecessary services: msconfig -> Services -> Hide Microsoft services -> Disable third-party.
            8. Check Event Viewer: Windows Logs -> System -> Filter for errors during boot time range.
            9. For HDDs: Defragment. For SSDs: Ensure TRIM enabled and AHCI mode.""",
            severity="LOW",
            keywords="slow boot, long startup, boot time slow, windows takes forever to start, slow startup, boot delay"
        )
        boot_dual, _ = self._rule(
            "BOOT-005", "Boot", "Dual Boot / GRUB Issues", "solution",
            """Dual Boot / GRUB Issues
            Linux/Windows dual boot menu missing or GRUB corrupted.
            1. Boot from Linux live USB: Any distro with live environment.
            2. Reinstall GRUB:
               sudo mount /dev/sdXY /mnt  (where sdXY is Linux root partition)
               sudo grub-install --boot-directory=/mnt/boot /dev/sdX
               sudo update-grub
            3. For UEFI systems:
               sudo mount /dev/sdXY /mnt
               sudo mount /dev/sdX1 /mnt/boot/efi  (EFI partition)
               sudo grub-install --target=x86_64-efi --efi-directory=/mnt/boot/efi --bootloader-id=GRUB
            4. Windows overwriting GRUB: After Windows update, GRUB may be replaced. Reinstall GRUB as above.
            5. Use boot-repair tool: Boot-Repair live CD automates common GRUB fixes.
            6. Check EFI boot order: efibootmgr to verify GRUB is in boot priority.
            7. rEFInd bootloader: Alternative to GRUB. Easier dual-boot management. Install from live USB.
            8. Back up EFI partition: Before major updates, back up EFI partition to USB.""",
            severity="MEDIUM",
            keywords="dual boot, grub, linux windows dual boot, grub rescue, bootloader, ubuntu boot, efi boot"
        )
        self._opt(boot_q, "Windows won't start / BCD error", boot_bcd, 0)
        self._opt(boot_q, "No boot device detected", boot_disk, 1)
        self._opt(boot_q, "Stuck in automatic repair loop", boot_loop, 2)
        self._opt(boot_q, "Boot is very slow", boot_slow, 3)
        self._opt(boot_q, "Dual boot / GRUB problems", boot_dual, 4)
        self.stdout.write("   5 nodes")
        return 5

    # =================================================================
    #  BIOS (5 nodes)
    # =================================================================

    def _seed_bios(self):
        self.stdout.write("  BIOS...")
        bios_q, _ = self._rule(
            "BIOS-Q1", "BIOS", "BIOS Issue Detection", "question",
            "Are you having BIOS or firmware-related issues?",
            keywords="bios, uefi, firmware, cmos, bios update, bios settings"
        )
        bios_update, _ = self._rule(
            "BIOS-001", "BIOS", "BIOS Update Failed / Bricked", "solution",
            """BIOS Update Failed / Bricked Motherboard
            BIOS update interrupted or failed, system won't POST.
            1. Don't panic: Many modern boards have recovery features.
            2. ASUS Flashback: Insert USB with renamed BIOS file into dedicated USB port. Press Flashback button. No CPU/RAM needed.
            3. MSI Flash BIOS Button: Similar to ASUS. USB with MSI.ROM in root, press button.
            4. Gigabyte Q-Flash Plus: USB with GIGABYTE.bin, press Q-Flash Plus button.
            5. Dual BIOS: Some boards have physical switch or automatic fallback to backup BIOS.
            6. External programmer: CH341A programmer with SOIC8 clip can reflash BIOS chip directly. Requires technical skill.
            7. RMA: If no recovery features work, contact motherboard manufacturer. BIOS bricking is often covered under warranty.
            8. Prevention: Always use UPS during BIOS update. Never update BIOS from Windows utility. Use built-in BIOS flash tool.
            9. Verify file: Ensure correct BIOS file for exact motherboard revision. Wrong file = brick.""",
            severity="CRITICAL",
            keywords="bios bricked, bios update failed, flashback, q flash, bios recovery, motherboard dead after update"
        )
        bios_settings, _ = self._rule(
            "BIOS-002", "BIOS", "BIOS Settings Confusion", "solution",
            """BIOS Settings Confusion
            Overwhelmed by BIOS options or changed something and system is unstable.
            1. Load optimized defaults: F5 or "Load Optimized Defaults" in BIOS. This is always safe.
            2. Key settings to know:
               - XMP/DOCP: Enables RAM rated speed. Safe for most systems.
               - Boot order: Which drive to boot from first.
               - CSM (Compatibility Support Module): Enable for Legacy/BIOS OS, disable for pure UEFI.
               - Secure Boot: Required for Windows 11. Disable for Linux dual boot or older OS.
               - Above 4G Decoding + Resizable BAR: Enable for modern GPUs. 5-10% performance boost.
               - TPM: Enable for Windows 11. fTPM (AMD) or PTT (Intel).
            3. Don't change what you don't understand: Voltage settings, LLC, and advanced timings can damage hardware.
            4. Save profile: Before experimenting, save current settings to profile slot or USB.
            5. Documentation: Read motherboard manual. It explains every BIOS option specific to your board.
            6. Community: r/overclocking and manufacturer forums have guides for your specific board.""",
            severity="LOW",
            keywords="bios settings, bios confusing, what to change in bios, bios options, uefi settings, bios guide"
        )
        bios_password, _ = self._rule(
            "BIOS-003", "BIOS", "Forgot BIOS Password", "solution",
            """Forgot BIOS Password
            Can't access BIOS due to forgotten administrator password.
            1. Check motherboard manual: Look for "Clear CMOS" or "Password Reset" jumper location.
            2. Clear CMOS: Remove CMOS battery for 5-10 minutes. This resets ALL BIOS settings including password.
            3. Use jumper: Short the CMOS clear pins with screwdriver or jumper cap for 10 seconds.
            4. For laptops: BIOS passwords are often stored in EEPROM and can't be cleared by removing battery. Contact manufacturer with proof of purchase.
            5. Manufacturer backdoor: Some older BIOSes have master passwords. Search "[manufacturer] BIOS master password".
            6. EEPROM programmer: Advanced users can read and modify BIOS chip directly to remove password.
            7. Never use BIOS password unless necessary: It's easy to forget and hard to recover. Use Windows password instead.
            8. Write it down: If you must use BIOS password, store it in a password manager.""",
            severity="MEDIUM",
            keywords="forgot bios password, bios locked, cant enter bios, clear cmos password, bios admin password"
        )
        bios_tpm, _ = self._rule(
            "BIOS-004", "BIOS", "TPM / Secure Boot for Windows 11", "solution",
            """TPM / Secure Boot for Windows 11
            Windows 11 requires TPM 2.0 and Secure Boot. Here's how to enable them.
            1. Enable TPM:
               - Intel: BIOS -> Advanced -> PTT (Platform Trust Technology) -> Enabled
               - AMD: BIOS -> Advanced -> fTPM (Firmware TPM) -> Enabled
            2. Enable Secure Boot:
               - BIOS -> Boot -> Secure Boot -> Enabled
               - May need to set OS Type to "Windows UEFI Mode" first
               - If switching from CSM, disable CSM first
            3. Check status: Run tpm.msc and msinfo32. Both should show TPM 2.0 present and Secure Boot On.
            4. If Secure Boot shows Off after enabling: Keys may not be enrolled. Look for "Restore Factory Keys" option.
            5. Windows 11 upgrade: PC Health Check app will verify requirements. If TPM is off, it will fail.
            6. Bypass (not recommended): Registry edits can bypass TPM check. Not recommended for security reasons.
            7. UEFI required: Windows 11 needs UEFI boot mode. MBR/Legacy BIOS installations won't work without conversion.
            8. Backup before conversion: GPT/MBR conversion can destroy data. Back up first.""",
            severity="LOW",
            keywords="tpm 2.0, secure boot, windows 11 requirements, fTPM, PTT, enable tpm, windows 11 compatible"
        )
        bios_overclock, _ = self._rule(
            "BIOS-005", "BIOS", "Overclocking Stability Issues", "solution",
            """Overclocking Stability Issues
            System crashes or won't boot after overclocking attempts.
            1. Clear CMOS: Remove battery or use jumper. This resets all overclock settings to safe defaults.
            2. Safe boot: Some BIOSes have "Safe Boot" or "Fail-Safe" mode that loads minimal settings.
            3. Reduce overclock: If system boots but crashes under load, reduce clock speed or increase voltage slightly.
            4. Check temperatures: Overclocking increases heat. Ensure cooling is adequate before proceeding.
            5. Stability testing: Use Prime95, AIDA64, or OCCT. Run for at least 1 hour. Any error = unstable.
            6. Incremental approach: Increase frequency in small steps (50MHz), test, then increase more.
            7. Voltage safety: Don't exceed manufacturer recommended max voltage. For Intel 12th/13th gen, 1.3V is generally safe daily limit.
            8. LLC (Load Line Calibration): Higher LLC reduces vdroop but increases voltage spikes. Start with medium LLC.
            9. Memory overclock: XMP is technically an overclock. If XMP unstable, try lower profile or manual timings.
            10. Know when to stop: 24/7 overclocks should be conservative. Benchmark overclocks can be pushed harder.""",
            severity="MEDIUM",
            keywords="overclock unstable, oc crash, overclock wont boot, bios overclock, cpu overclock fail, reset overclock"
        )
        self._opt(bios_q, "BIOS update failed / bricked motherboard", bios_update, 0)
        self._opt(bios_q, "Confused by BIOS settings / changed something wrong", bios_settings, 1)
        self._opt(bios_q, "Forgot BIOS password", bios_password, 2)
        self._opt(bios_q, "Need TPM/Secure Boot for Windows 11", bios_tpm, 3)
        self._opt(bios_q, "Overclocking caused instability", bios_overclock, 4)
        self.stdout.write("   5 nodes")
        return 5

    # =================================================================
    #  Display (5 nodes)
    # =================================================================

    def _seed_display(self):
        self.stdout.write("  Display...")
        disp_q, _ = self._rule(
            "DISP-Q1", "Display", "Display Issue Detection", "question",
            "Are you having monitor or display output problems?",
            keywords="monitor, display, screen, resolution, hdmi, displayport, black screen"
        )
        disp_no_signal, _ = self._rule(
            "DISP-001", "Display", "No Signal / Black Screen", "solution",
            """No Signal / Black Screen
            Monitor shows "No Signal" despite system appearing to power on.
            1. Check cable connection: Ensure firmly seated at both monitor and GPU/motherboard ends.
            2. Try different cable: Cables can fail. Test with known-good HDMI, DP, or DVI cable.
            3. Try different port: GPU may have multiple outputs. Test HDMI vs DisplayPort vs DVI.
            4. Check monitor input: Ensure monitor is set to correct input source (HDMI1, DP, etc.).
            5. Test monitor on another device: If monitor works with laptop/another PC, monitor is fine.
            6. Test with integrated graphics: Remove GPU, connect to motherboard video output.
            7. Check GPU seating: GPU may have popped out of PCIe slot slightly. Reseat firmly.
            8. Check power: Some monitors have separate power brick. Ensure LED on monitor power button lights up.
            9. Wake from sleep: Press keyboard/mouse. Some monitors don't wake properly from sleep. Disable monitor sleep as test.""",
            severity="HIGH",
            keywords="no signal, black screen, monitor no signal, display not working, blank monitor, no display output"
        )
        disp_flicker, _ = self._rule(
            "DISP-002", "Display", "Screen Flickering / Tearing", "solution",
            """Screen Flickering / Tearing
            Display flickers, shows horizontal lines, or tears during motion.
            1. Check cable quality: Cheap or damaged cables cause flickering. Use certified cables, especially for high refresh rates.
            2. Check refresh rate: Windows -> Display Settings -> Advanced Display -> Refresh rate. Should match monitor capability.
            3. Enable VSync / G-Sync / FreeSync: Tearing occurs when frame rate doesn't match refresh rate. Enable in GPU control panel and game.
            4. Update GPU drivers: Outdated drivers cause display artifacts and flickering.
            5. Check for interference: Route display cables away from power cables. EMI can cause flickering.
            6. Lower refresh rate test: If 144Hz flickers but 60Hz is stable, cable or GPU output may be insufficient.
            7. Check monitor settings: Some monitors have overdrive settings. Too aggressive overdrive causes inverse ghosting.
            8. Test different GPU: If flickering follows the GPU, GPU output is failing. If it follows the monitor, monitor is failing.
            9. Power supply: Insufficient or failing PSU can cause GPU output instability, manifesting as flicker.""",
            severity="MEDIUM",
            keywords="screen flicker, display flickering, screen tearing, horizontal lines, monitor flicker, vsync, gsync"
        )
        disp_resolution, _ = self._rule(
            "DISP-003", "Display", "Wrong Resolution / Scaling Issues", "solution",
            """Wrong Resolution / Scaling Issues
            Display shows wrong resolution, blurry text, or UI elements too small/large.
            1. Set native resolution: Windows -> Display Settings -> Resolution -> Select monitor's native resolution.
            2. Update GPU drivers: Generic drivers often limit resolution. Install manufacturer drivers.
            3. Check scaling: Windows -> Display Settings -> Scale and layout. 100% for 1080p, 125-150% for 1440p, 150-200% for 4K.
            4. ClearType: Search "ClearType" in Start menu. Run wizard to optimize text rendering.
            5. DPI scaling per app: Right-click app -> Properties -> Compatibility -> Change high DPI settings -> Override scaling.
            6. Check cable type: VGA and some DVI cables can't carry high resolutions. Use HDMI 2.0+ or DisplayPort 1.2+.
            7. Multiple monitors: Windows sometimes applies wrong scaling to secondary monitors. Set per-monitor scaling.
            8. EDID issues: If monitor not reporting correct resolution, use Custom Resolution Utility (CRU) to override EDID.
            9. macOS: System Preferences -> Displays -> Scaled. Hold Option while clicking Scaled for more options.""",
            severity="LOW",
            keywords="wrong resolution, blurry screen, scaling issues, dpi scaling, text too small, 4k scaling, resolution problem"
        )
        disp_color, _ = self._rule(
            "DISP-004", "Display", "Color Accuracy / Calibration", "solution",
            """Color Accuracy / Calibration
            Colors look wrong, washed out, or oversaturated on your monitor.
            1. Check monitor settings: Most monitors have preset modes (Standard, sRGB, Game, Movie). sRGB is usually most accurate.
            2. Windows calibration: Search "Calibrate display color" in Start menu. Follow wizard to adjust gamma, brightness, contrast.
            3. Use calibration tool: X-Rite i1Display or Datacolor Spyder for professional calibration.
            4. Check color profile: Windows -> Color Management -> Ensure correct ICC profile is assigned to monitor.
            5. NVIDIA/AMD settings: Control panel may have "Digital vibrance" or color saturation sliders. Reset to default.
            6. HDR issues: HDR can make SDR content look washed out. Disable HDR for non-HDR content, or use Auto HDR.
            7. Night Light / f.lux: These shift colors to warmer tones. Disable for color-critical work.
            8. Panel type: TN panels have poor color accuracy. IPS and OLED are better. Know your panel's limitations.
            9. Professional work: For photo/video editing, calibrate monthly. Ambient light changes affect perception.""",
            severity="LOW",
            keywords="color accuracy, monitor calibration, washed out colors, oversaturated, display color wrong, icc profile, gamma"
        )
        disp_multi, _ = self._rule(
            "DISP-005", "Display", "Multi-Monitor Setup Issues", "solution",
            """Multi-Monitor Setup Issues
            Problems with multiple monitors not detected, wrong arrangement, or different behaviors.
            1. Check all connections: Each monitor needs its own cable to GPU. Daisy-chaining only works with DisplayPort MST.
            2. Detect displays: Windows -> Display Settings -> Detect. Sometimes Windows doesn't auto-detect on boot.
            3. Arrange displays: Drag monitor icons to match physical layout. This determines mouse movement direction.
            4. Set primary display: Check "Make this my main display" on preferred monitor.
            5. Match refresh rates: Different refresh rates can cause stuttering on some systems. Try matching all to same rate.
            6. Taskbar on all displays: Settings -> Personalization -> Taskbar -> Taskbar behaviors -> Show taskbar on all displays.
            7. Different scaling per monitor: Set per-monitor scaling in Display Settings. May require logout/login.
            8. GPU output limits: Check GPU specs for max simultaneous displays. Older GPUs may only support 2-3.
            9. USB-C/Thunderbolt docks: Some docks have display output limits. Check dock specifications.""",
            severity="LOW",
            keywords="multi monitor, dual monitor, second monitor not detected, monitor arrangement, display settings, multiple screens"
        )
        self._opt(disp_q, "Monitor shows no signal / black screen", disp_no_signal, 0)
        self._opt(disp_q, "Screen flickers or tears", disp_flicker, 1)
        self._opt(disp_q, "Wrong resolution or blurry text", disp_resolution, 2)
        self._opt(disp_q, "Colors look wrong / need calibration", disp_color, 3)
        self._opt(disp_q, "Multi-monitor setup problems", disp_multi, 4)
        self.stdout.write("   5 nodes")
        return 5

    # =================================================================
    #  Network (5 nodes)
    # =================================================================

    def _seed_network(self):
        self.stdout.write("  Network...")
        net_q, _ = self._rule(
            "NET-Q1", "Network", "Network Issue Detection", "question",
            "Are you experiencing network or internet connectivity problems?",
            keywords="network, internet, wifi, ethernet, connection, router, modem"
        )
        net_no_internet, _ = self._rule(
            "NET-001", "Network", "No Internet Connection", "solution",
            """No Internet Connection
            Can't access websites or online services.
            1. Check other devices: If phone also has no internet, problem is with ISP/router, not your PC.
            2. Restart router/modem: Unplug for 30 seconds, plug back in. Wait 2 minutes for full boot.
            3. Check Ethernet cable: Ensure firmly seated. Try different cable. Look for link lights on port.
            4. Check WiFi: Ensure connected to correct network. Forget network and reconnect.
            5. Run Windows Network Troubleshooter: Settings -> Network & Internet -> Network troubleshooter.
            6. Release/renew IP: Command Prompt (admin) -> ipconfig /release then ipconfig /renew.
            7. Flush DNS: ipconfig /flushdns
            8. Check DNS settings: Set to 8.8.8.8 and 8.8.4.4 (Google) or 1.1.1.1 (Cloudflare).
            9. Disable VPN/proxy: These can block all traffic if misconfigured.
            10. Check firewall: Windows Defender or third-party firewall may be blocking all traffic.""",
            severity="HIGH",
            keywords="no internet, no connection, cant access websites, offline, network down, internet not working"
        )
        net_slow, _ = self._rule(
            "NET-002", "Network", "Slow Internet / High Latency", "solution",
            """Slow Internet / High Latency
            Internet is slower than expected or online games lag.
            1. Speed test: Use fast.com or speedtest.net. Compare to your ISP plan.
            2. Check WiFi signal: Weak signal = slow speeds. Move closer to router or use Ethernet.
            3. Interference: 2.4GHz is crowded. Switch to 5GHz or 6GHz if router supports it.
            4. Bandwidth hogs: Check if someone is streaming 4K or downloading large files.
            5. QoS settings: Router QoS can prioritize gaming/video traffic over downloads.
            6. Ping test: ping 8.8.8.8 -t. High ping (>100ms) or packet loss = ISP or router issue.
            7. DNS switch: Slow DNS can make browsing feel slow. Try 1.1.1.1 or 8.8.8.8.
            8. Update router firmware: Old firmware has bugs and security vulnerabilities.
            9. Ethernet vs WiFi: Ethernet is always more stable and faster. Use for gaming and work.
            10. Contact ISP: If speeds are consistently below plan, ISP may have infrastructure issues.""",
            severity="MEDIUM",
            keywords="slow internet, high ping, lag, slow download, slow upload, network slow, wifi slow, latency"
        )
        net_wifi, _ = self._rule(
            "NET-003", "Network", "WiFi Connection Issues", "solution",
            """WiFi Connection Issues
            Can't connect to WiFi, or connection drops frequently.
            1. Check WiFi is enabled: Some laptops have physical switch or Fn key combo. Check airplane mode.
            2. Restart WiFi adapter: Device Manager -> Network adapters -> Right-click WiFi -> Disable, then Enable.
            3. Update WiFi driver: Download from laptop/motherboard manufacturer or WiFi chip maker (Intel, Realtek, MediaTek).
            4. Forget and reconnect: Settings -> WiFi -> Forget network, then reconnect with password.
            5. Check router: Restart router. Ensure firmware is updated. Check for MAC filtering.
            6. WiFi channel: Use WiFi Analyzer app to find least congested channel. Set router to that channel.
            7. 5GHz vs 2.4GHz: 5GHz is faster but shorter range. 2.4GHz penetrates walls better but is slower.
            8. WiFi extender/mesh: If signal is weak in some rooms, add mesh node or extender.
            9. USB WiFi adapter: If built-in WiFi is failing, a $15 USB adapter is a quick fix.
            10. Interference: Microwaves, cordless phones, and baby monitors interfere with 2.4GHz.""",
            severity="MEDIUM",
            keywords="wifi not working, cant connect to wifi, wifi drops, wifi disconnecting, wireless issues, wifi adapter"
        )
        net_ethernet, _ = self._rule(
            "NET-004", "Network", "Ethernet Connection Issues", "solution",
            """Ethernet Connection Issues
            Wired connection not working or intermittent.
            1. Check link lights: Both PC and router/switch port should have green/orange lights.
            2. Try different cable: Cables can fail internally. Try a known-good Cat5e or Cat6 cable.
            3. Try different port: Router/switch ports can fail. Test with another port.
            4. Update network driver: Device Manager -> Network adapters -> Ethernet -> Update driver.
            5. Check speed/duplex: Device Manager -> Ethernet -> Properties -> Advanced -> Speed & Duplex. Set to Auto Negotiation.
            6. Disable power saving: Device Manager -> Ethernet -> Power Management -> Uncheck "Allow computer to turn off this device".
            7. Check for bent pins: RJ45 connector pins can bend. Look inside connector with flashlight.
            8. Test with USB Ethernet adapter: If built-in port is failing, USB adapter is a quick workaround.
            9. Cable length: Ethernet has 100m max length. Longer runs need switch/repeater.
            10. Check for EMI: Run cables away from power lines and fluorescent lights.""",
            severity="MEDIUM",
            keywords="ethernet not working, wired connection, lan not working, ethernet cable, network port, no lan"
        )
        net_router, _ = self._rule(
            "NET-005", "Network", "Router / Modem Problems", "solution",
            """Router / Modem Problems
            Router not working, needs configuration, or has issues.
            1. Power cycle: Unplug router AND modem for 30 seconds. Plug modem in first, wait for full boot, then router.
            2. Check indicator lights: Most routers have status LEDs. Red or flashing = problem. Check manual for meaning.
            3. Factory reset: Hold reset button for 10+ seconds. Reconfigure from scratch.
            4. Update firmware: Log into router admin panel (usually 192.168.1.1) and check for updates.
            5. Change default password: Default admin passwords are security risks. Change immediately.
            6. Check ISP status: Visit ISP website or call support. Outages happen.
            7. Port forwarding: For gaming servers or remote access, configure port forwarding in router settings.
            8. DMZ: For troubleshooting, place one device in DMZ to rule out router firewall issues.
            9. Bridge mode: If using separate modem and router, ensure modem is in bridge mode to avoid double NAT.
            10. Replace: Consumer routers last 3-5 years. If constantly rebooting or dropping, replace it.""",
            severity="HIGH",
            keywords="router not working, modem problem, wifi router, network hardware, router setup, internet router"
        )
        self._opt(net_q, "No internet at all", net_no_internet, 0)
        self._opt(net_q, "Internet is very slow or high ping", net_slow, 1)
        self._opt(net_q, "WiFi won't connect or keeps dropping", net_wifi, 2)
        self._opt(net_q, "Ethernet not working", net_ethernet, 3)
        self._opt(net_q, "Router/modem issues", net_router, 4)
        self.stdout.write("   5 nodes")
        return 5

    # =================================================================
    #  Peripherals (5 nodes)
    # =================================================================

    def _seed_peripherals(self):
        self.stdout.write("  Peripherals...")
        per_q, _ = self._rule(
            "PER-Q1", "Peripherals", "Peripheral Issue Detection", "question",
            "Are you having problems with keyboards, mice, or other external devices?",
            keywords="keyboard, mouse, peripheral, usb device, external, input device"
        )
        per_keyboard, _ = self._rule(
            "PER-001", "Peripherals", "Keyboard Not Working", "solution",
            """Keyboard Not Working
            Keyboard is unresponsive or keys don't register.
            1. Check connection: Unplug and replug. Try different USB port. Test on another PC.
            2. Check Num Lock: If Num Lock is off, numpad won't work. Press Num Lock key.
            3. Clean keyboard: Turn upside down and shake. Use compressed air between keys.
            4. Sticky keys: Remove keycap carefully and clean underneath with isopropyl alcohol and cotton swab.
            5. Update drivers: Device Manager -> Keyboards -> Update driver. Or use manufacturer software.
            6. Check for spills: Liquid damage can cause shorts. If recently spilled, dry thoroughly for 48+ hours.
            7. Wireless keyboard: Check battery. Re-pair with USB receiver. Try different USB port for receiver.
            8. BIOS test: If keyboard doesn't work in BIOS, it's hardware failure. Replace keyboard.
            9. Mechanical switches: If one key fails, switch may be dead. Can be replaced if hot-swappable.
            10. Membrane keyboards: If multiple keys fail, membrane sheet is damaged. Usually not repairable.""",
            severity="MEDIUM",
            keywords="keyboard not working, keys not registering, keyboard dead, typing not working, keyboard unresponsive"
        )
        per_mouse, _ = self._rule(
            "PER-002", "Peripherals", "Mouse Not Working / Erratic", "solution",
            """Mouse Not Working / Erratic Behavior
            Mouse doesn't move, clicks don't register, or cursor jumps around.
            1. Check connection: Unplug and replug. Try different USB port. Test on another PC.
            2. Clean sensor: Use cotton swab with isopropyl alcohol on optical sensor on bottom.
            3. Clean mouse feet: Dirty feet cause inconsistent tracking. Clean with damp cloth.
            4. Check surface: Optical mice need consistent texture. Glass and glossy surfaces don't work well.
            5. Mouse pad: Use a proper mouse pad. Even a sheet of paper is better than bare desk.
            6. Update drivers: Device Manager -> Mice and other pointing devices -> Update driver.
            7. Wireless mouse: Check battery. Re-pair receiver. Try closer to receiver (within 1 meter).
            8. Interference: Other 2.4GHz devices (WiFi, Bluetooth) can interfere with wireless mouse.
            9. Double-clicking: Mechanical switch degradation. Can be fixed by replacing switch (soldering required).
            10. Cursor jumping: High DPI setting or surface issue. Lower DPI in mouse software or change surface.""",
            severity="MEDIUM",
            keywords="mouse not working, cursor jumping, mouse erratic, mouse clicks not working, wireless mouse, mouse dead"
        )
        per_printer, _ = self._rule(
            "PER-003", "Peripherals", "Printer Issues", "solution",
            """Printer Issues
            Printer not printing, showing errors, or poor print quality.
            1. Check power and connections: Ensure printer is on and connected (USB or network).
            2. Check paper: Ensure correct paper size loaded. Check for jams. Remove and reload tray.
            3. Check ink/toner: Most printers show ink levels. Replace if low or empty.
            4. Run printer troubleshooter: Settings -> Bluetooth & devices -> Printers -> Run troubleshooter.
            5. Clear print queue: Services.msc -> Print Spooler -> Stop. Delete contents of C:\\Windows\\System32\\spool\\PRINTERS. Restart Print Spooler.
            6. Reinstall driver: Remove printer, download latest driver from manufacturer website, reinstall.
            7. Network printer: Ensure printer and PC are on same network. Check printer IP address.
            8. Print test page: From printer settings or control panel. If test page fails, it's hardware.
            9. Clean print heads: Use printer's built-in cleaning function. Run 2-3 times if clogged.
            10. Alignment: Run alignment utility after replacing cartridges for best print quality.""",
            severity="LOW",
            keywords="printer not working, wont print, print error, printer offline, poor print quality, ink problem"
        )
        per_usb, _ = self._rule(
            "PER-004", "Peripherals", "USB Device Not Recognized", "solution",
            """USB Device Not Recognized
            Windows shows "USB device not recognized" or device doesn't appear.
            1. Try different port: Front panel ports sometimes have loose internal cables. Try rear motherboard ports.
            2. Try different cable: USB cables can fail internally while looking fine.
            3. Try different PC: If device works on another computer, your USB port or driver is the issue.
            4. Update USB drivers: Device Manager -> Universal Serial Bus controllers -> Update all.
            5. Check power: Some USB devices need more power than a single port provides. Use powered USB hub.
            6. Disable USB selective suspend: Power Options -> Change plan settings -> Change advanced power settings -> USB settings -> Disable selective suspend.
            7. Check for driver signature: Some devices need unsigned drivers. Disable driver signature enforcement temporarily.
            8. Check Device Manager for errors: Yellow triangle indicates driver or hardware problem.
            9. USB 2.0 vs 3.0: Some older devices don't work well on USB 3.0 (blue) ports. Try black USB 2.0 port.
            10. BIOS: Ensure USB ports are enabled in BIOS. Some boards allow disabling individual ports.""",
            severity="MEDIUM",
            keywords="usb not recognized, device not recognized, usb error, unknown usb device, usb port not working"
        )
        per_bluetooth, _ = self._rule(
            "PER-005", "Peripherals", "Bluetooth Issues", "solution",
            """Bluetooth Issues
            Bluetooth devices won't pair, disconnect, or have poor audio quality.
            1. Check Bluetooth is on: Settings -> Bluetooth & devices -> Bluetooth toggle.
            2. Check device is in pairing mode: Most devices need to be held in pairing mode to be discoverable.
            3. Remove and re-pair: Settings -> Bluetooth -> Remove device, then pair again.
            4. Update Bluetooth driver: Device Manager -> Bluetooth -> Update driver.
            5. Check range: Bluetooth has ~10m range. Walls reduce this significantly.
            6. Interference: WiFi (2.4GHz), microwaves, and cordless phones interfere with Bluetooth.
            7. Audio quality: For headphones, ensure A2DP profile is selected, not HSP/HFP (which is phone-call quality).
            8. Battery: Low battery on Bluetooth device causes disconnections and poor audio.
            9. USB Bluetooth adapter: If built-in Bluetooth is failing, a $10 USB dongle is a quick fix.
            10. Windows Bluetooth stack: Sometimes Windows Bluetooth stack gets corrupted. Remove all paired devices and restart.""",
            severity="LOW",
            keywords="bluetooth not working, cant pair bluetooth, bluetooth disconnecting, bluetooth audio, bluetooth pairing"
        )
        self._opt(per_q, "Keyboard not working", per_keyboard, 0)
        self._opt(per_q, "Mouse not working or erratic", per_mouse, 1)
        self._opt(per_q, "Printer issues", per_printer, 2)
        self._opt(per_q, "USB device not recognized", per_usb, 3)
        self._opt(per_q, "Bluetooth problems", per_bluetooth, 4)
        self.stdout.write("   5 nodes")
        return 5

    # =================================================================
    #  Audio (5 nodes)
    # =================================================================

    def _seed_audio(self):
        self.stdout.write("  Audio...")
        aud_q, _ = self._rule(
            "AUD-Q1", "Audio", "Audio Issue Detection", "question",
            "Are you experiencing sound or audio-related problems?",
            keywords="audio, sound, speaker, headphone, microphone, no sound"
        )
        aud_no_sound, _ = self._rule(
            "AUD-001", "Audio", "No Sound Output", "solution",
            """No Sound Output
            No audio from speakers or headphones.
            1. Check volume: Ensure system volume is up and not muted. Check physical mute button on keyboard.
            2. Check output device: Click speaker icon in taskbar -> Select correct output device.
            3. Check connections: Ensure speakers/headphones are plugged into correct port (green = line out).
            4. Test with different device: Try headphones on phone. If they work, PC audio is the issue.
            5. Update audio driver: Device Manager -> Sound, video and game controllers -> Update driver.
            6. Run audio troubleshooter: Settings -> System -> Sound -> Troubleshoot.
            7. Check Windows Audio service: Services.msc -> Windows Audio -> Ensure Running and Automatic.
            8. Check front panel audio: Front panel connectors may be loose. Try rear motherboard audio ports.
            9. Disable audio enhancements: Right-click speaker -> Properties -> Enhancements -> Disable all enhancements.
            10. BIOS: Ensure onboard audio is enabled in BIOS. Some boards disable it when GPU is installed.""",
            severity="MEDIUM",
            keywords="no sound, no audio, speakers not working, headphones no sound, audio not working, silent"
        )
        aud_distorted, _ = self._rule(
            "AUD-002", "Audio", "Distorted / Crackling Audio", "solution",
            """Distorted / Crackling Audio
            Audio sounds crackly, distorted, or has static.
            1. Check cable: Loose or damaged audio cables cause crackling. Try different cable.
            2. Check connector: Ensure 3.5mm jack is fully inserted. Partial insertion causes distortion.
            3. Update audio driver: Outdated drivers cause audio glitches. Download from motherboard manufacturer.
            4. Change audio format: Sound settings -> Device properties -> Additional device properties -> Advanced -> Try different sample rate (e.g., 44100 Hz or 48000 Hz).
            5. Disable enhancements: Right-click speaker -> Properties -> Enhancements -> Disable all.
            6. Check for electrical interference: Route audio cables away from power cables and GPU.
            7. Ground loop: Hum/buzz caused by ground loop. Use ground loop isolator or plug all devices into same power strip.
            8. DAC/Amp: If onboard audio is poor, external USB DAC or sound card improves quality significantly.
            9. Check headphones on another device: If distortion follows headphones, they are damaged.
            10. DPC latency: High DPC latency causes audio dropouts. Use LatencyMon to diagnose.""",
            severity="MEDIUM",
            keywords="distorted audio, crackling sound, static noise, audio glitch, buzzing sound, poor audio quality"
        )
        aud_mic, _ = self._rule(
            "AUD-003", "Audio", "Microphone Not Working", "solution",
            """Microphone Not Working
            Mic not detected or not picking up sound.
            1. Check mic is selected: Click speaker icon -> Input device -> Select correct microphone.
            2. Check mute: Ensure mic is not muted in Windows or on the physical device.
            3. Test mic: Settings -> System -> Sound -> Input -> Test your microphone.
            4. Check connections: Pink 3.5mm jack for analog mics. USB mics need firm USB connection.
            5. Update driver: Device Manager -> Audio inputs and outputs -> Update driver.
            6. Privacy settings: Settings -> Privacy -> Microphone -> Allow apps to access microphone.
            7. Boost mic level: Sound settings -> Device properties -> Additional device properties -> Levels -> Increase mic boost.
            8. Check app permissions: Some apps (Discord, Zoom) have their own mic selection and mute controls.
            9. Test in different app: If mic works in Windows test but not in Discord, it's an app setting.
            10. Physical damage: If mic was dropped or cable was yanked, internal wiring may be damaged.""",
            severity="MEDIUM",
            keywords="microphone not working, mic not detected, cant hear me, mic muted, microphone issue, voice not working"
        )
        aud_drivers, _ = self._rule(
            "AUD-004", "Audio", "Audio Driver Issues", "solution",
            """Audio Driver Issues
            Audio device not detected, code 10 errors, or driver conflicts.
            1. Uninstall and reinstall: Device Manager -> Audio device -> Uninstall device -> Restart. Windows will reinstall.
            2. Download from manufacturer: Don't use generic Windows drivers. Get Realtek, Creative, etc. from manufacturer.
            3. DDU for audio: Some audio drivers conflict. Use Driver Store Explorer to remove old audio drivers completely.
            4. Check for Windows updates: Some audio issues are fixed in Windows updates.
            5. BIOS audio setting: Ensure onboard audio is enabled. Some boards have HD Audio vs AC97 setting.
            6. Disable conflicting devices: If you have multiple audio devices (GPU HDMI audio, onboard, USB), disable unused ones.
            7. Code 10 error: Usually driver issue. Try different driver version (older or newer).
            8. IRQ conflicts: Rare on modern systems, but possible. Check Device Manager for resource conflicts.
            9. System restore: If audio broke after update, restore to previous restore point.
            10. Clean install: Last resort. Back up data and reinstall Windows if driver issues persist.""",
            severity="MEDIUM",
            keywords="audio driver, sound driver error, code 10, realtek driver, audio device not detected, driver conflict"
        )
        aud_hdmi, _ = self._rule(
            "AUD-005", "Audio", "HDMI / DisplayPort Audio Issues", "solution",
            """HDMI / DisplayPort Audio Issues
            No audio through monitor or TV connected via HDMI/DisplayPort.
            1. Select correct output: Click speaker icon -> Select monitor/TV as output device.
            2. Check monitor volume: Monitors have their own volume controls. Ensure not muted and turned up.
            3. Update GPU drivers: HDMI audio is part of GPU driver. Update NVIDIA/AMD/Intel graphics drivers.
            4. Check cable: Some cheap HDMI cables don't carry audio. Use certified High Speed HDMI cable.
            5. DisplayPort audio: Not all DisplayPort cables support audio. Use DP 1.2+ certified cable.
            6. Set as default: Sound settings -> Output -> Set monitor as default device.
            7. Check monitor input: Some monitors only play audio on specific inputs (e.g., HDMI 1 but not HDMI 2).
            8. GPU control panel: NVIDIA Control Panel -> Set up digital audio -> Ensure monitor is selected.
            9. Windows audio service: Restart Windows Audio service if HDMI audio disappears after sleep.
            10. EDID issue: Monitor not reporting audio capability. Use Custom Resolution Utility to override EDID.""",
            severity="LOW",
            keywords="hdmi audio, displayport audio, no sound through monitor, tv audio, hdmi no sound, monitor speakers"
        )
        self._opt(aud_q, "No sound at all", aud_no_sound, 0)
        self._opt(aud_q, "Audio is distorted or crackling", aud_distorted, 1)
        self._opt(aud_q, "Microphone not working", aud_mic, 2)
        self._opt(aud_q, "Audio driver errors", aud_drivers, 3)
        self._opt(aud_q, "No audio through HDMI/DisplayPort", aud_hdmi, 4)
        self.stdout.write("   5 nodes")
        return 5

    # =================================================================
    #  Laptop (6 nodes)
    # =================================================================

    def _seed_laptop(self):
        self.stdout.write("  Laptop...")
        lap_q, _ = self._rule(
            "LAP-Q1", "Laptop", "Laptop Issue Detection", "question",
            "Are you experiencing problems specific to your laptop?",
            keywords="laptop, notebook, battery, charging, screen, hinge, touchpad"
        )
        lap_battery, _ = self._rule(
            "LAP-001", "Laptop", "Battery / Charging Issues", "solution",
            """Battery / Charging Issues
            Laptop won\'t charge, battery drains fast, or won\'t run without AC adapter.
            1. Check power adapter: Ensure LED on adapter brick is on. Try different outlet.
            2. Reseat battery: If removable, remove and reinsert battery. Clean contacts with eraser.
            3. Reset battery: Some laptops have pinhole reset button. Press with paperclip for 30 seconds.
            4. Calibrate battery: Charge to 100%, discharge completely, charge to 100% again.
            5. Check battery health: powercfg /batteryreport in Command Prompt. Check cycle count and capacity.
            6. Update BIOS: Some charging issues are fixed in BIOS updates.
            7. Check charging port: Wiggle charger. If intermittent, charging port may be loose or damaged.
            8. Replace battery: After 300-500 cycles, lithium batteries lose significant capacity.
            9. Third-party chargers: Ensure wattage matches or exceeds original. Underpowered chargers charge slowly or not at all.
            10. Windows power settings: Settings -> System -> Power -> Check sleep and screen timeout settings.""",
            severity="MEDIUM",
            keywords="laptop battery, wont charge, battery drain, charging port, power adapter, battery replacement"
        )
        lap_overheat, _ = self._rule(
            "LAP-002", "Laptop", "Laptop Overheating", "solution",
            """Laptop Overheating
            Laptop gets very hot, fans run constantly, or thermal throttles.
            1. Clean vents: Use compressed air to blow out dust from intake and exhaust vents.
            2. Elevate laptop: Use a stand or even a book to improve airflow underneath.
            3. Cooling pad: External USB cooling pad with fans helps significantly.
            4. Check thermal paste: After 2-3 years, thermal paste dries out. Repaste CPU/GPU (advanced, may void warranty).
            5. Check for blocked vents: Don\'t use laptop on soft surfaces (bed, couch) that block vents.
            6. Undervolt CPU: Intel XTU or ThrottleStop can reduce voltage by 50-100mV, lowering temps 5-10C.
            7. Limit turbo: Disable turbo boost or limit turbo time in ThrottleStop for sustained workloads.
            8. Check for malware: Crypto-miners max out CPU and cause overheating.
            9. BIOS fan curves: Some laptops allow adjusting fan curves in BIOS.
            10. Thermal pads: Replace dried thermal pads on VRMs and VRAM if repasting.""",
            severity="HIGH",
            keywords="laptop hot, laptop overheating, fan loud, thermal throttle, laptop temperature, cooling pad"
        )
        lap_screen, _ = self._rule(
            "LAP-003", "Laptop", "Laptop Screen Issues", "solution",
            """Laptop Screen Issues
            Screen is dim, flickers, has lines, or is physically damaged.
            1. Check brightness: Ensure not turned down via Fn key. Check adaptive brightness is off.
            2. External monitor test: Connect HDMI/DisplayPort. If external works, laptop screen or cable is faulty.
            3. Loose cable: Laptop screen cable runs through hinge. Opening/closing can loosen it.
            4. Inverter/backlight: If screen is very dim but you can see image with flashlight, backlight or inverter failed.
            5. Dead pixels: 1-2 dead pixels = normal manufacturing tolerance. Many dead pixels = warranty claim.
            6. Physical damage: Cracked screen must be replaced. Check if covered under accidental damage warranty.
            7. Screen replacement: Find exact panel model (usually on back of panel). Buy replacement on eBay/AliExpress.
            8. Touchscreen issues: If touch doesn\'t work, check Device Manager for HID-compliant touch screen.
            9. Flickering: Often caused by loose cable or failing backlight. Can also be GPU issue (see GPU-001).
            10. Lines on screen: Vertical/horizontal lines usually indicate panel failure, not GPU.""",
            severity="HIGH",
            keywords="laptop screen, cracked screen, dim screen, screen flicker, dead pixels, backlight, screen replacement"
        )
        lap_keyboard, _ = self._rule(
            "LAP-004", "Laptop", "Laptop Keyboard / Touchpad Issues", "solution",
            """Laptop Keyboard / Touchpad Issues
            Built-in keyboard or touchpad not working properly.
            1. Check Fn lock: Some laptops have Fn+Esc or similar to lock Fn state. This changes key behavior.
            2. Disable/enable: Device Manager -> Keyboards/Mice -> Disable then Enable device.
            3. Check for spills: Liquid damage is common. If spilled, power off immediately and dry for 48+ hours.
            4. Driver update: Download keyboard/touchpad drivers from laptop manufacturer (not generic Windows).
            5. Touchpad disabled: Many laptops have Fn key combo to disable touchpad. Check for accidental press.
            6. Palm rejection: Overly aggressive palm rejection can cause cursor jumps. Adjust in touchpad settings.
            7. Physical damage: If keys are physically broken, individual keys or entire keyboard assembly can be replaced.
            8. Ribbon cable: Keyboard and touchpad connect via ribbon cables to motherboard. Reseat if comfortable.
            9. External test: USB keyboard/mouse working confirms internal hardware issue, not software.
            10. BIOS test: If keyboard doesn\'t work in BIOS, it\'s definitely hardware failure.""",
            severity="MEDIUM",
            keywords="laptop keyboard, touchpad not working, keyboard spill, laptop keys broken, touchpad disabled, cursor jump"
        )
        lap_hinge, _ = self._rule(
            "LAP-005", "Laptop", "Laptop Physical Damage / Hinge", "solution",
            """Laptop Physical Damage / Hinge Problems
            Hinge is loose, cracked, or screen separates from body.
            1. Stop forcing it: If hinge is stiff, forcing it cracks the plastic mounting points.
            2. Check screws: Some hinge screws are accessible from bottom panel. Tighten if loose.
            3. Plastic vs metal: Plastic hinge mounts break easily. Metal mounts are more durable but still fail.
            4. Temporary fix: Tape can hold screen in position temporarily. Not a long-term solution.
            5. Replacement: Buy hinge set for exact laptop model on eBay/AliExpress. Requires disassembly.
            6. Professional repair: If uncomfortable disassembling, laptop repair shops charge $50-150 for hinge repair.
            7. Case damage: If plastic mounting points are broken, epoxy or JB Weld can rebuild them (advanced).
            8. Prevent future damage: Always open laptop from center, not corner. Don\'t carry by screen.
            9. Warranty: Some manufacturers cover hinge defects. Check warranty terms.
            10. Upgrade opportunity: If laptop is old, consider whether repair cost is worth it vs replacement.""",
            severity="LOW",
            keywords="laptop hinge, broken hinge, screen loose, laptop case cracked, physical damage, laptop repair"
        )
        self._opt(lap_q, "Battery won\'t charge / drains fast", lap_battery, 0)
        self._opt(lap_q, "Laptop gets very hot", lap_overheat, 1)
        self._opt(lap_q, "Screen problems (dim, cracked, lines)", lap_screen, 2)
        self._opt(lap_q, "Keyboard or touchpad not working", lap_keyboard, 3)
        self._opt(lap_q, "Hinge or physical damage", lap_hinge, 4)
        self.stdout.write("   5 nodes")
        return 5

    # =================================================================
    #  General (6 nodes)
    # =================================================================

    def _seed_general(self):
        self.stdout.write("  General...")
        gen_q, _ = self._rule(
            "GEN-Q1", "General", "General System Issue Detection", "question",
            "Are you experiencing general system issues that don\'t fit other categories?",
            keywords="general, system, performance, slow, freeze, crash, windows"
        )
        gen_slow, _ = self._rule(
            "GEN-001", "General", "General System Slowdown", "solution",
            """General System Slowdown
            Overall system feels sluggish and unresponsive.
            1. Check resource usage: Task Manager -> Performance. High CPU/RAM/Disk = identify culprit process.
            2. Startup programs: Task Manager -> Startup -> Disable everything non-essential.
            3. Disk cleanup: cleanmgr -> Clean system files. Remove temp files, old Windows updates.
            4. Uninstall bloatware: Control Panel -> Programs -> Remove manufacturer bloatware and unused apps.
            5. Check for malware: Run full scan with Windows Defender or Malwarebytes.
            6. Update Windows: Settings -> Windows Update -> Check for updates. Some updates fix performance issues.
            7. Update all drivers: Use manufacturer tools (Intel Driver & Support Assistant, AMD Auto-Detect, NVIDIA GeForce Experience).
            8. Check thermal throttling: High temps cause slowdown. See CPU-001 for cooling fixes.
            9. RAM upgrade: If consistently using >80% RAM, adding more RAM is the best upgrade for general responsiveness.
            10. SSD upgrade: Replacing HDD with SSD is the single biggest performance upgrade for most systems.
            11. Fresh install: After 2-3 years of use, Windows accumulates cruft. Backup and clean install restores performance.""",
            severity="MEDIUM",
            keywords="system slow, computer sluggish, slow performance, unresponsive, laggy, general slowdown"
        )
        gen_freeze, _ = self._rule(
            "GEN-002", "General", "System Freezes / Hangs", "solution",
            """System Freezes / Hangs
            System becomes completely unresponsive, requiring hard reset.
            1. Check Event Viewer: Windows Logs -> System -> Look for errors just before freeze time.
            2. Check temperatures: Overheating CPU/GPU causes freezes. See CPU-001 and GPU-001.
            3. RAM test: Faulty RAM causes freezes. Run MemTest86 (see RAM-003).
            4. PSU test: Failing PSU causes freezes under load. See PSU-001.
            5. Driver issues: Recently updated driver? Roll back in Device Manager.
            6. Windows update: Some updates cause freezes. Uninstall recent updates.
            7. Check disk health: Failing SSD/HDD causes system hangs. See STO-002.
            8. Disable overclock: Unstable overclocks cause freezes. Reset to stock in BIOS.
            9. Check peripherals: Faulty USB device can freeze system. Disconnect all non-essential USB devices.
            10. BIOS update: Some freezes are fixed in newer BIOS versions.
            11. Clean boot: msconfig -> Selective startup -> Load only Microsoft services. If stable, third-party software is culprit.""",
            severity="HIGH",
            keywords="system freeze, computer hangs, unresponsive, frozen screen, system lockup, hard freeze"
        )
        gen_crash, _ = self._rule(
            "GEN-003", "General", "Random Crashes / Blue Screens (BSOD)", "solution",
            """Random Crashes / Blue Screens (BSOD)
            System crashes with blue screen showing error code.
            1. Note the error code: Each BSOD has a code (e.g., IRQL_NOT_LESS_OR_EQUAL, PAGE_FAULT_IN_NONPAGED_AREA).
            2. Check minidump: C:\\Windows\\Minidump -> Analyze with BlueScreenView or WinDbg.
            3. Common codes and causes:
               - MEMORY_MANAGEMENT = RAM issue (see RAM-003)
               - IRQL_NOT_LESS_OR_EQUAL = Driver issue
               - PAGE_FAULT_IN_NONPAGED_AREA = RAM or driver
               - KERNEL_SECURITY_CHECK_FAILURE = Corrupted system files
               - CRITICAL_PROCESS_DIED = Corrupted Windows or failing drive
               - WHEA_UNCORRECTABLE_ERROR = Hardware failure (CPU/RAM)
            4. Update drivers: Especially chipset, GPU, and network drivers.
            5. Run sfc /scannow and DISM: Fixes corrupted system files.
            6. Check RAM: Run MemTest86 (see RAM-003).
            7. Check drive health: See STO-002.
            8. Check temperatures: Overheating causes crashes. See CPU-001.
            9. Recent changes: If BSOD started after hardware/software change, undo it.
            10. WhoCrashed: Free tool that analyzes minidumps and suggests causes.""",
            severity="CRITICAL",
            keywords="bsod, blue screen, crash, system crash, blue screen of death, windows crash, error code"
        )
        gen_virus, _ = self._rule(
            "GEN-004", "General", "Malware / Virus Infection", "solution",
            """Malware / Virus Infection
            Suspect computer is infected with malware, virus, or unwanted software.
            1. Disconnect internet: Prevents malware from communicating with command server or spreading.
            2. Boot to Safe Mode: Many malwares don\'t load in Safe Mode. Easier to clean.
            3. Run scans:
               - Windows Defender full scan
               - Malwarebytes free scan
               - AdwCleaner for adware/toolbars
               - HitmanPro for second opinion
            4. Check browser extensions: Remove unknown extensions. Reset browser settings.
            5. Check startup: Task Manager -> Startup -> Disable suspicious entries.
            6. Check scheduled tasks: Task Scheduler -> Look for suspicious tasks running malware.
            7. Check hosts file: C:\\Windows\\System32\\drivers\\etc\\hosts -> Should not have many entries.
            8. Check proxy settings: Some malware routes traffic through malicious proxy.
            9. If heavily infected: Backup personal files, then clean install Windows. Safer than trying to clean.
            10. Prevention:
                - Keep Windows updated
                - Use ad blocker (uBlock Origin)
                - Don\'t download from untrusted sites
                - Don\'t open unexpected email attachments""",
            severity="CRITICAL",
            keywords="virus, malware, trojan, ransomware, infected, computer virus, remove malware, antivirus"
        )
        gen_upgrade, _ = self._rule(
            "GEN-005", "General", "System Upgrade / Build Advice", "solution",
            """System Upgrade / Build Advice
            Planning to upgrade or build a new PC.
            1. Define budget and use case: Gaming, content creation, office work, or server have very different needs.
            2. Gaming priority: GPU > CPU > RAM > SSD. Spend 40-50% of budget on GPU.
            3. Content creation: CPU and RAM matter more. 32GB+ RAM, 8+ core CPU, mid-range GPU sufficient.
            4. Compatibility: Use PCPartPicker to check compatibility between CPU, motherboard, RAM, and case.
            5. PSU quality: Never cheap out on PSU. 80+ Gold from Corsair, EVGA, Seasonic, be quiet!.
            6. Future-proofing: Buy motherboard with next-gen features (PCIe 5.0, DDR5) if budget allows.
            7. Used market: GPUs and CPUs hold value well. Consider used for budget builds.
            8. Prebuilt vs DIY: Prebuilt is easier and sometimes cheaper (GPU shortage periods). DIY offers better quality parts.
            9. Monitor matters: A $2000 PC with a $100 monitor wastes potential. Budget 20% for monitor.
            10. Peripherals: Mechanical keyboard, good mouse, and quality headset improve experience more than expected.
            11. When to upgrade vs build new: If upgrading CPU requires new motherboard and RAM, consider full build.""",
            severity="LOW",
            keywords="pc build, upgrade advice, build a pc, computer upgrade, which parts to buy, pc building guide"
        )
        self._opt(gen_q, "System is generally slow", gen_slow, 0)
        self._opt(gen_q, "System freezes or hangs", gen_freeze, 1)
        self._opt(gen_q, "Blue screens / random crashes", gen_crash, 2)
        self._opt(gen_q, "Suspect malware or virus", gen_virus, 3)
        self._opt(gen_q, "Planning to upgrade or build new PC", gen_upgrade, 4)
        self.stdout.write("   5 nodes")
        return 5
