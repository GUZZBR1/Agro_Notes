<?php

declare(strict_types=1);

namespace Drupal\farm_test\Drush\Commands;

use Drupal\Core\DependencyInjection\AutowireTrait;
use Drupal\Core\Extension\ModuleExtensionList;
use Drupal\Core\Extension\ModuleInstallerInterface;
use Drush\Attributes as CLI;
use Drush\Commands\DrushCommands;

/**
 * Farm Test Drush commands.
 *
 * @ingroup farm
 */
final class FarmTestCommands extends DrushCommands {

  use AutowireTrait;

  public function __construct(
    protected ModuleExtensionList $moduleExtensionList,
    protected ModuleInstallerInterface $moduleInstaller,
  ) {
    parent::__construct();
  }

  /**
   * Install all farmOS modules.
   */
  #[CLI\Command(name: 'farm_test:modules')]
  #[CLI\Usage(name: 'farm_test:modules', description: 'Install all farmOS modules.')]
  public function modules() {

    // List the packages that we care about.
    $packages = [
      'farmOS',
      'farmOS Taxonomies',
      'farmOS Assets',
      'farmOS Logs',
      'farmOS Quantities',
      'farmOS Organizations',
      'farmOS Defaults',
      'farmOS Roles',
      'farmOS Maps',
      'farmOS UI',
      'farmOS Quick Forms',
      'farmOS (Experimental)',
      'farmOS (Legacy)',
    ];

    // Build a list of modules, filtered by package.
    $modules = array_filter($this->moduleExtensionList->getAllAvailableInfo(), function ($module_info) use ($packages) {
      return isset($module_info['package']) && in_array($module_info['package'], $packages);
    });

    // Install all modules.
    $this->moduleInstaller->install(array_keys($modules), TRUE);
  }

}
