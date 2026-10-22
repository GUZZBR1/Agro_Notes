<?php

declare(strict_types=1);

namespace Drupal\farm_update;

use Drupal\Core\Config\ConfigFactoryInterface;
use Drupal\Core\Entity\EntityTypeManagerInterface;
use Drupal\Core\Extension\ModuleHandlerInterface;
use Drupal\Core\StringTranslation\StringTranslationTrait;
use Drupal\config_update\ConfigDiffer;
use Drupal\config_update\ConfigListerWithProviders;
use Drupal\config_update\ConfigReverter;
use Psr\Log\LoggerInterface;
use Symfony\Component\DependencyInjection\Attribute\Autowire;

/**
 * Farm update service.
 *
 * @internal
 */
class FarmUpdate implements FarmUpdateInterface {

  use StringTranslationTrait;

  public function __construct(
    #[Autowire(service: 'logger.channel.farm_update')]
    protected LoggerInterface $logger,
    protected ModuleHandlerInterface $moduleHandler,
    protected EntityTypeManagerInterface $entityTypeManager,
    protected ConfigFactoryInterface $configFactory,
    #[Autowire(service: 'config_update.config_diff')]
    protected ConfigDiffer $configDiff,
    #[Autowire(service: 'config_update.config_list')]
    protected ConfigListerWithProviders $configList,
    #[Autowire(service: 'config_update.config_update')]
    protected ConfigReverter $configUpdate,
  ) {}

  /**
   * {@inheritdoc}
   */
  public function rebuild(): void {

    // Get a list of managed config.
    $managed_config = $this->getManagedConfig();

    // Build a list of config to revert.
    $revert_config = array_intersect($this->getDifferentItems('type', 'system.all'), $managed_config);

    // Iterate through config items and revert them.
    foreach ($revert_config as $name) {

      // Get the config type and bail if simple configuration.
      // The lister gives NULL if simple configuration.
      /** @var string|null $type */
      $type = $this->configList->getTypeNameByConfigName($name);
      if ($type === NULL) {
        continue;
      }

      // Get the config short name.
      $shortname = $this->getConfigShortname($type, $name);

      // Perform the operation.
      $result = $this->configUpdate->revert($type, $shortname);

      // Log the result.
      if ($result) {
        $this->logger->notice('Reverted config: @config', ['@config' => $name]);
      }
      else {
        $this->logger->error('Failed to revert config: @config', ['@config' => $name]);
      }
    }
  }

  /**
   * Lists managed config items.
   *
   * Lists config items that should be automatically updated.
   *
   * @return array
   *   An array of config item names.
   */
  protected function getManagedConfig() {

    // Ask modules for managed configuration items.
    $managed_config = $this->moduleHandler->invokeAll('farm_update_managed_config');

    // Load farm_update.settings to get additional items.
    $settings_managed_config = $this->configFactory->get('farm_update.settings')->get('managed_config');
    if (!empty($settings_managed_config)) {
      $managed_config = array_merge($managed_config, $settings_managed_config);
    }

    // Allow modules to alter the list of managed configuration items.
    $this->moduleHandler->alter('farm_update_managed_config', $managed_config);

    return $managed_config;
  }

  /**
   * Lists differing config items.
   *
   * Lists config items that differ from the versions provided by your
   * installed modules, themes, or install profile. See config-diff to show
   * what the differences are.
   *
   * This method is copied directly from ConfigUpdateUiCommands.
   *
   * @param string $type
   *   Run the report for: module, theme, profile, or "type" for config entity
   *   type.
   * @param string $name
   *   The machine name of the module, theme, etc. to report on. See
   *   config-list-types to list types for config entities; you can also use
   *   system.all for all types, or system.simple for simple config.
   *
   * @return array
   *   An array of differing configuration items.
   *
   * @see \Drupal\config_update_ui\Commands\ConfigUpdateUiCommands::getDifferentItems()
   */
  protected function getDifferentItems($type, $name) {
    [$activeList, $installList, $optionalList] = $this->configList->listConfig($type, $name);
    $addedItems = array_diff($activeList, $installList, $optionalList);
    $activeAndAddedItems = array_diff($activeList, $addedItems);
    $differentItems = [];
    foreach ($activeAndAddedItems as $name) {
      $active = $this->configUpdate->getFromActive('', $name);
      $extension = $this->configUpdate->getFromExtension('', $name);
      if (!$this->configDiff->same($active, $extension)) {
        $differentItems[] = $name;
      }
    }
    sort($differentItems);

    return $differentItems;
  }

  /**
   * Gets the config item shortname given the type and name.
   *
   * This method is copied directly from ConfigUpdateUiCommands.
   *
   * @param string $type
   *   The type of the config item.
   * @param string $name
   *   The name of the config item.
   *
   * @return string
   *   The shortname for the configuration item.
   *
   * @see \Drupal\config_update_ui\Commands\ConfigUpdateUiCommands::getConfigShortname()
   */
  protected function getConfigShortname($type, $name) {
    $shortname = $name;
    if ($type != 'system.simple') {
      /** @var \Drupal\Core\Config\Entity\ConfigEntityTypeInterface $definition */
      $definition = $this->entityTypeManager->getDefinition($type);
      $prefix = $definition->getConfigPrefix() . '.';
      if (str_starts_with($name, $prefix)) {
        $shortname = substr($name, strlen($prefix));
      }
    }

    return $shortname;
  }

}
