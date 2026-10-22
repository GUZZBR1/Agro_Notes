<?php

declare(strict_types=1);

namespace Drupal\farm_export_csv\Plugin\Action;

use Drupal\Core\Action\Attribute\Action;
use Drupal\Core\Action\Plugin\Action\EntityActionBase;
use Drupal\Core\Entity\EntityTypeManagerInterface;
use Drupal\Core\Session\AccountInterface;
use Drupal\Core\StringTranslation\TranslatableMarkup;
use Drupal\Core\TempStore\PrivateTempStoreFactory;
use Symfony\Component\DependencyInjection\ContainerInterface;

/**
 * Action that exports a CSV file of log quantities.
 */
#[Action(
  id: 'farm_export_csv:log_quantity',
  action_label: new TranslatableMarkup('Export Quantities CSV'),
  confirm_form_route_name: 'entity.quantity.csv_form',
  type: 'log',
)]
class LogQuantityCsv extends EntityActionBase {

  public function __construct(
    array $configuration,
    $plugin_id,
    $plugin_definition,
    EntityTypeManagerInterface $entity_type_manager,
    protected PrivateTempStoreFactory $tempStoreFactory,
    protected AccountInterface $currentUser,
  ) {
    parent::__construct($configuration, $plugin_id, $plugin_definition, $entity_type_manager);
  }

  /**
   * {@inheritdoc}
   */
  public static function create(ContainerInterface $container, array $configuration, $plugin_id, $plugin_definition) {
    // @todo Use autowiring and remove this when the parent class does.
    // @see https://www.drupal.org/project/drupal/issues/3552110
    return new static(
      $configuration,
      $plugin_id,
      $plugin_definition,
      $container->get('entity_type.manager'),
      $container->get('tempstore.private'),
      $container->get('current_user'),
    );
  }

  /**
   * {@inheritdoc}
   */
  public function executeMultiple(array $entities) {
    $quantities = array_reduce($entities, function ($carry, $entity) {
      array_push($carry, ...$entity->get('quantity')->referencedEntities());
      return $carry;
    }, []);
    /** @var \Drupal\Core\Entity\EntityInterface[] $entities */
    $this->tempStoreFactory->get('entity_csv_confirm')->set($this->currentUser->id() . ':quantity', $quantities);
  }

  /**
   * {@inheritdoc}
   */
  public function execute($object = NULL) {
    $this->executeMultiple([$object]);
  }

  /**
   * {@inheritdoc}
   */
  public function access($object, ?AccountInterface $account = NULL, $return_as_object = FALSE) {
    return $object->access('view', $account, $return_as_object);
  }

}
